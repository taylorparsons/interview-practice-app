import logging
import os
import asyncio
import textwrap
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request
import httpx
import uvicorn
from openai import AsyncOpenAI

# Import local modules
from app.config import (
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_REALTIME_MODEL,
    OPENAI_REALTIME_VOICE, OPENAI_REALTIME_URL,
    OPENAI_TURN_DETECTION, OPENAI_TURN_THRESHOLD, OPENAI_TURN_PREFIX_MS, OPENAI_TURN_SILENCE_MS,
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS,
    KNOWLEDGE_STORE_DIR, WORK_HISTORY_STORE_FILE,
    OPENAI_INPUT_TRANSCRIPTION_MODEL,
)
from app.utils.document_processor import allowed_file, save_uploaded_file, save_text_as_file, process_documents
from app.models.interview_agent import (
    InterviewPracticeAgent,
    InterviewAgentConfig,
    get_base_coach_prompt,
    get_voice_system_prompt,
)
from app.logging_config import setup_logging
from app.logging_context import session_id_var
from app.middleware.request_logging import RequestLoggingMiddleware
from app.utils.embedding_store import get_work_history_store
from app.utils.session_store import (
    save_session as persist_session,
    load_session as load_persisted_session,
    delete_session as delete_persisted_session,
    rename_session as rename_persisted_session,
    list_sessions as list_persisted_sessions,
)

setup_logging()
logger = logging.getLogger(__name__)


def log_event(slug: str, *, level: str = "info", session_id: Optional[str] = None, **fields: Any) -> None:
    """Emit a structured log with a verb-noun slug and optional context."""
    extra = {"session_id": session_id}
    for key, value in fields.items():
        if value is None:
            continue
        extra[f"ctx_{key}"] = value
    log_fn = getattr(logger, level, logger.info)
    log_fn(slug, extra=extra)


def _coach_display_name(persona: Optional[str]) -> Optional[str]:
    """Return the human-friendly label for a coach persona slug."""
    mapping = {
        "ruthless": "Ruthless Coach",
        "helpful": "Helpful Coach",
        "discovery": "Discovery Coach",
    }
    return mapping.get((persona or "").lower() or "", None)


_EXAMPLE_ANSWER_RESPONSES: List[tuple[tuple[str, ...], str]] = [
    (
        ("experience", "background"),
        """I have over 5 years of experience in software development with a focus on full-stack web applications. My background includes working at both startups and established companies where I've contributed to all stages of the software development lifecycle. In my most recent role at TechCorp, I led the development of a customer-facing portal that increased customer engagement by 35% and reduced support tickets by 20%. Prior to that, I worked at InnovateX where I built RESTful APIs that improved system performance by 40%. My technical expertise includes JavaScript/TypeScript, React, Node.js, Python, and SQL databases.""",
    ),
    (
        ("strengths",),
        """My greatest professional strengths include technical problem-solving, effective communication, and adaptive learning. When faced with complex technical challenges, I methodically break them down into manageable components and systematically address each one. This approach helped me resolve a critical performance bottleneck in our production system that had been affecting users for weeks. Additionally, I excel at communicating technical concepts to non-technical stakeholders, which has been valuable when working with product managers and business teams. Lastly, I prioritize continuous learning to stay current with emerging technologies and best practices, regularly dedicating time to explore new tools and techniques that could benefit our projects.""",
    ),
    (
        ("weaknesses",),
        """One area I've been working to improve is delegating responsibilities more effectively. In the past, I would take on too many tasks myself, which sometimes led to burnout. I've addressed this by implementing a structured approach to task management and team coordination, focusing on identifying team members' strengths and aligning tasks accordingly. I've also been working on balancing technical perfectionism with practical deadlines, recognizing when something is 'good enough' for an initial release versus when perfection is truly necessary. Through regular feedback and reflection, I've made significant progress in both areas, which has improved both my productivity and work-life balance.""",
    ),
    (
        ("interest", "why"),
        """I'm particularly interested in this position because it aligns perfectly with my technical skills and career aspirations. The opportunity to work on innovative solutions that directly impact users is exciting to me. I've been following your company's growth and am impressed by your commitment to both technical excellence and user experience. The job description mentioned responsibilities around optimizing application performance and implementing new features, which are areas where I have demonstrated success in previous roles. Additionally, your company culture of continuous learning and collaborative problem-solving resonates with my personal work values. I believe my background in similar technologies and experience solving comparable challenges would allow me to make meaningful contributions quickly.""",
    ),
    (
        ("five years", "future"),
        """In five years, I envision myself having deepened my technical expertise while also growing my leadership skills. I aim to become a senior developer who not only contributes high-quality code but also mentors junior team members and influences technical decisions. I'm particularly interested in continuing to specialize in distributed systems while gaining more experience with cloud architecture and scalability challenges. I also plan to further develop my project management skills to potentially move into a technical lead role where I can help bridge the gap between technical implementation and business objectives. Throughout this journey, I'll remain committed to continuous learning and staying current with emerging technologies and methodologies.""",
    ),
]

_EXAMPLE_ANSWER_DEFAULT = """Based on my experience and qualifications, I would approach this by leveraging my technical skills and domain knowledge. I believe in combining theoretical understanding with practical implementation, always focusing on delivering value while maintaining code quality and system performance. When facing challenges in this area, I rely on systematic problem-solving, collaboration with team members, and staying current with industry best practices. In my previous roles, I've successfully handled similar situations by breaking down complex problems into manageable components, prioritizing user needs, and implementing solutions that are both robust and scalable. I'm always eager to learn and adapt, which I believe is essential in our rapidly evolving field."""


def _example_answer_fallback(question: Optional[str]) -> str:
    """Provide a canned example answer when the agent cannot produce one."""
    prompt = (question or "").lower()
    for keywords, response in _EXAMPLE_ANSWER_RESPONSES:
        if any(keyword in prompt for keyword in keywords):
            return response
    return _EXAMPLE_ANSWER_DEFAULT

# Initialize FastAPI
app = FastAPI(title="Interview Practice App")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Install structured request logging middleware (request id, timings)
app.add_middleware(RequestLoggingMiddleware)

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Store active interview sessions
active_sessions = {}


def _allowed_import_roots() -> List[Path]:
    """Return allowed root directories for work-history imports."""
    roots = {
        Path(UPLOAD_FOLDER).resolve(),
        KNOWLEDGE_STORE_DIR.resolve(),
    }
    extra = os.getenv("WORK_HISTORY_IMPORT_ALLOWED_ROOTS")
    if extra:
        for raw in extra.split(os.pathsep):
            raw = raw.strip()
            if not raw:
                continue
            try:
                roots.add(Path(raw).expanduser().resolve())
            except Exception:
                log_event(
                    "knowledge.import.allowlist_invalid",
                    level="warning",
                    entry=raw,
                )
    return list(roots)


def _resolve_import_path(path_str: str) -> Path:
    """Validate that the requested import path lives under an allowed root."""
    candidate = Path(path_str).expanduser().resolve()
    for root in _allowed_import_roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    log_event(
        "knowledge.import.disallowed_path",
        level="warning",
        path=str(candidate),
    )
    raise HTTPException(status_code=403, detail="Import path not permitted")


def _get_session(session_id: str) -> Dict[str, Any]:
    """Retrieve a session from memory or disk, raising 404 when missing."""
    session = active_sessions.get(session_id)
    if session is not None:
        return session

    stored = load_persisted_session(session_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")

    active_sessions[session_id] = stored
    return stored


def _persist_session_state(session_id: str, session: Dict[str, Any]) -> None:
    """Update the in-memory cache and persist session state to disk."""
    active_sessions[session_id] = session
    persist_session(session_id, session)


async def _ensure_agent_ready(session_id: str, session: Dict[str, Any], *, force_restart: bool = False) -> Dict[str, Any]:
    """Ensure an agent is ready for the session, optionally forcing a restart."""
    try:
        session_id_var.set(session_id)
    except Exception:
        pass
    if force_restart and session.get("agent") is not None:
        log_event("agent.ensure.reset", session_id=session_id)
        session["agent"] = None
        _persist_session_state(session_id, session)

    if session.get("agent") is None:
        log_event("agent.ensure.start", session_id=session_id)
        try:
            await start_agent(session_id)
        except Exception:
            log_event("agent.ensure.error", level="exception", session_id=session_id)
        session = _get_session(session_id)
        if session.get("agent") is None:
            log_event("agent.ensure.unavailable", level="warning", session_id=session_id)
        else:
            log_event("agent.ensure.ready", session_id=session_id)

    return session


def _derive_session_name(job_desc_text: str) -> str:
    """Heuristically derive a session name as 'title_company' from job description text."""
    if not job_desc_text:
        return "untitled_session"
    text = (job_desc_text or "").strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    head = "\n".join(lines[:20])  # examine first ~20 non-empty lines

    import re

    # Try explicit fields
    title_match = re.search(r"(?im)^(?:job\s*title|title|position|role)\s*:\s*(.+)$", head)
    comp_match = re.search(r"(?im)^(?:company|employer|organization)\s*:\s*(.+)$", head)

    title = title_match and title_match.group(1).strip()
    company = comp_match and comp_match.group(1).strip()

    # Try 'Title at Company'
    if not (title and company) and lines:
        at_match = re.search(r"(?im)^(.{3,80}?)\s+at\s+([A-Za-z0-9 &\-.,]{2,80})$", lines[0])
        if at_match:
            if not title:
                title = at_match.group(1).strip()
            if not company:
                company = at_match.group(2).strip()

    # Try 'Company - Title' or 'Title - Company'
    if not (title and company) and lines:
        dash_line = lines[0]
        if "-" in dash_line:
            parts = [p.strip() for p in dash_line.split("-") if p.strip()]
            if len(parts) >= 2:
                # Assume first is title, second is company
                title = title or parts[0]
                company = company or parts[1]

    # Fallbacks
    title = title or "position"
    company = company or "company"

    def slugify(s: str) -> str:
        """Normalize free-form text into a filesystem-safe slug."""
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s or "item"

    return f"{slugify(title)}_{slugify(company)}"


# Request and response models
class DocumentUploadResponse(BaseModel):
    """Response payload returned after successful resume/job description upload."""
    session_id: str
    message: str
    name: Optional[str] = None


class GenerateQuestionsRequest(BaseModel):
    """Request body for generating interview questions."""
    session_id: str
    num_questions: int = 5


class GenerateQuestionsResponse(BaseModel):
    """Model encapsulating generated interview questions."""
    questions: List[str]


class EvaluateAnswerRequest(BaseModel):
    """Request payload for evaluating a candidate answer."""
    session_id: str
    question: str
    answer: str
    voice_transcript: Optional[str] = None


class EvaluateAnswerResponse(BaseModel):
    """Model describing the structured evaluation from the coach."""
    evaluation: Dict[str, Any]


class ExampleAnswerRequest(BaseModel):
    """Request envelope asking for an example answer to a question."""
    session_id: str
    question: str


class ExampleAnswerResponse(BaseModel):
    """Response model containing a sample answer from the coach."""
    answer: str


class VoiceSessionRequest(BaseModel):
    """Parameters required to create a realtime voice coaching session."""
    session_id: str
    voice: Optional[str] = None
    agent_name: Optional[str] = None
    persona: Optional[str] = None


class VoiceSessionResponse(BaseModel):
    """Details returned from the realtime voice session provisioning API."""
    id: str
    model: str
    client_secret: str
    url: str
    expires_at: Optional[int] = None


class SessionListItem(BaseModel):
    """Summary metadata describing a saved interview session."""
    id: str
    name: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    questions_count: Optional[int] = 0
    answers_count: Optional[int] = 0


class RenameSessionRequest(BaseModel):
    """Request body for renaming an existing session."""
    name: str


class SaveTranscriptRequest(BaseModel):
    """Body payload for persisting a voice transcript snippet."""
    question_index: int
    text: str
    source: Optional[str] = None


class SaveAgentTextRequest(BaseModel):
    """Payload for storing the coach's spoken feedback text."""
    question_index: int
    text: str


# Work history / knowledge store models
class WorkHistoryChunk(BaseModel):
    """Single chunk of text plus optional metadata destined for the knowledge store."""
    text: str
    metadata: Optional[Dict[str, Any]] = None


class WorkHistoryAddRequest(BaseModel):
    """Request wrapper for adding multiple knowledge store chunks at once."""
    chunks: List[WorkHistoryChunk]


class WorkHistoryImportPathRequest(BaseModel):
    """Request describing a filesystem path whose contents should be ingested."""
    path: str


class MemorizeTranscriptRequest(BaseModel):
    """Request body for storing a transcript or its summary in the knowledge store."""
    question_index: Optional[int] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    summarize: bool = False


class SetCoachPersonaRequest(BaseModel):
    """Request model for updating the active coach persona of a session."""
    persona: str


# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload-documents", response_model=DocumentUploadResponse)
async def upload_documents(
    resume: UploadFile = File(...),
    job_description: Optional[UploadFile] = File(None),
    job_description_text: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
):
    # Validate resume file
    if not allowed_file(resume.filename):
        raise HTTPException(status_code=400, detail="Invalid resume file format")

    job_description_text = job_description_text or ""

    # Ensure either a file or text was provided for the job description
    if job_description is None and not job_description_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Provide a job description file or paste the job description text.",
        )

    if job_description is not None and not allowed_file(job_description.filename):
        raise HTTPException(status_code=400, detail="Invalid job description file format")
    
    # Create session ID
    session_id = str(uuid.uuid4())
    try:
        session_id_var.set(session_id)
    except Exception:
        pass
    log_event(
        "session.create.start",
        session_id=session_id,
        resume_filename=resume.filename,
        job_filename=job_description.filename if job_description is not None else None,
        job_text_chars=len(job_description_text or ""),
    )

    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Save uploaded files or text
    resume_path = save_uploaded_file(resume, UPLOAD_FOLDER, session_id + "_resume")
    if job_description is not None:
        job_desc_path = save_uploaded_file(job_description, UPLOAD_FOLDER, session_id + "_job_description")
    else:
        job_desc_path = save_text_as_file(job_description_text, UPLOAD_FOLDER, session_id + "_job_description")
    
    # Process documents
    resume_text, job_desc_text = await process_documents(resume_path, job_desc_path)
    
    # Store session data
    default_name = _derive_session_name(job_desc_text)
    session_data = {
        "resume_path": resume_path,
        "job_desc_path": job_desc_path,
        "resume_text": resume_text,
        "job_desc_text": job_desc_text,
        "name": default_name,
        "coach_persona": "discovery",
        "questions": [],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    _persist_session_state(session_id, session_data)
    log_event(
        "session.create.persisted",
        session_id=session_id,
        name=default_name,
        resume_chars=len(resume_text or ""),
        job_chars=len(job_desc_text or ""),
    )

    # Initialize and start the agent in the background
    if background_tasks:
        background_tasks.add_task(start_agent, session_id)
        log_event("agent.start.enqueued", session_id=session_id)

    return {"session_id": session_id, "message": "Documents uploaded successfully", "name": default_name}


@app.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    session_id = request.session_id
    session = _get_session(session_id)
    try:
        session_id_var.set(session_id)
    except Exception:
        pass
    log_event(
        "questions.generate.start",
        session_id=session_id,
        requested=request.num_questions,
        agent_present=bool(session.get("agent")),
    )

    if session.get("agent") is not None:
        try:
            agent = session["agent"]
            questions = await agent.generate_interview_questions(request.num_questions)

            session["questions"] = questions
            session["current_question_index"] = 0
            _persist_session_state(session_id, session)
            log_event(
                "questions.generate.agent",
                session_id=session_id,
                count=len(questions),
            )

            return {"questions": questions}
        except Exception:
            log_event("questions.generate.error", level="exception", session_id=session_id)

    job_desc = session["job_desc_text"] if "job_desc_text" in session else ""
    
    default_questions = [
        "Tell me about your experience and background.",
        "What are your greatest professional strengths?",
        "What do you consider to be your weaknesses?",
        "Why are you interested in this position?",
        "Where do you see yourself in five years?"
    ]
    questions = default_questions.copy()
    if job_desc and len(job_desc) > 100:
        keywords = ["python", "javascript", "react", "node", "aws", "cloud", "database", 
                   "sql", "nosql", "machine learning", "data", "frontend", "backend", 
                   "fullstack", "devops", "agile", "scrum"]
        
        job_specific_questions = []
        for keyword in keywords:
            if keyword.lower() in job_desc.lower():
                job_specific_questions.append(f"Can you describe your experience with {keyword}?")
        
        for i, question in enumerate(job_specific_questions[:3]):
            if i < len(default_questions):
                questions[i+2] = question  # Keep the first two default questions
    
    session["questions"] = questions
    session["current_question_index"] = 0
    _persist_session_state(session_id, session)
    log_event(
        "questions.generate.fallback",
        session_id=session_id,
        count=len(questions),
    )

    return {"questions": questions[:request.num_questions]}


@app.post("/evaluate-answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer(request: EvaluateAnswerRequest):
    session_id = request.session_id
    session = _get_session(session_id)
    # Bind session id into logging context for correlation
    try:
        session_id_var.set(session_id)
    except Exception:
        pass

    for attempt in range(2):
        session = await _ensure_agent_ready(session_id, session, force_restart=attempt > 0)
        agent = session.get("agent")
        if agent is None:
            continue
        try:
            # Determine question index and transcript (if any)
            try:
                idx = (session.get("questions") or []).index(request.question)
            except ValueError:
                idx = session.get("current_question_index", 0)
            # Prefer client-provided transcript, fall back to persisted
            transcript_text = (request.voice_transcript or "").strip()
            if not transcript_text:
                user_transcripts = session.get("voice_user_text") or {}
                transcripts = session.get("voice_transcripts") or {}
                transcript_text = (
                    user_transcripts.get(str(idx))
                    or user_transcripts.get(idx)
                    or transcripts.get(str(idx))
                    or transcripts.get(idx)
                    or ""
                )

            log_event(
                "evaluation.agent",
                session_id=session_id,
                attempt=attempt + 1,
                question_index=idx,
                question_chars=len(request.question or ""),
                answer_chars=len(request.answer or ""),
                transcript_present=bool(transcript_text and transcript_text.strip()),
            )
            evaluation = await agent.evaluate_answer(request.question, request.answer, transcript_text)

            if "answers" not in session:
                session["answers"] = []
            if "evaluations" not in session:
                session["evaluations"] = []

            session["answers"].append({"question": request.question, "answer": request.answer})
            session["evaluations"].append(evaluation)
            # Store per-question evaluation array for downstream summary rendering
            questions = session.get("questions") or []
            try:
                pidx = questions.index(request.question)
            except ValueError:
                pidx = len(session["answers"]) - 1
            perq = session.get("per_question") or [None] * len(questions)
            if len(perq) < len(questions):
                perq.extend([None] * (len(questions) - len(perq)))
            perq[pidx] = evaluation
            session["per_question"] = perq

            session["current_question_index"] = len(session["answers"])
            _persist_session_state(session_id, session)
            log_event(
                "evaluation.persisted",
                session_id=session_id,
                total_answers=len(session["answers"]),
                total_evaluations=len(session["evaluations"]),
            )

            return {"evaluation": evaluation}
        except Exception:
            log_event(
                "evaluation.agent.error",
                level="exception",
                session_id=session_id,
                attempt=attempt + 1,
            )
            # Drop the agent so a subsequent attempt can reinitialize
            session["agent"] = None
            _persist_session_state(session_id, session)
    
    log_event(
        "evaluation.fallback",
        session_id=session_id,
        question_chars=len(request.question or ""),
        answer_chars=len(request.answer or ""),
    )
    answer_length = len(request.answer)
    
    score = 0
    if answer_length > 500:
        score = min(9, 5 + answer_length // 200)  # Longer answers get higher scores, max 9
    elif answer_length > 200:
        score = 5 + answer_length // 200  # Medium answers get medium scores
    elif answer_length > 50:
        score = 3  # Short answers get lower scores
    else:
        score = 1  # Very short answers get very low scores
    
    strengths = []
    improvements = []
    
    if answer_length > 300:
        strengths.append("Provided a comprehensive response")
    if answer_length > 100 and answer_length <= 300:
        strengths.append("Answer was concise yet informative")
    if len(set(request.question.lower().split()).intersection(set(request.answer.lower().split()))) > 3:
        strengths.append("Directly addressed the question")
    
    if not strengths:
        possible_strengths = [
            "Demonstrated clear communication",
            "Showed logical thinking",
            "Provided structured response"
        ]
        strengths = [possible_strengths[answer_length % len(possible_strengths)]]
    
    if answer_length < 100:
        improvements.append("Consider providing more detail in your answer")
    if len(set(request.question.lower().split()).intersection(set(request.answer.lower().split()))) < 3:
        improvements.append("Try to more directly address the specific question")
    if answer_length > 500:
        improvements.append("Consider being more concise while maintaining key points")
    
    if not improvements:
        possible_improvements = [
            "Consider using more specific examples from your experience",
            "Try to relate your answer more to the job requirements",
            "Structure your answer with a clearer beginning, middle, and end"
        ]
        improvements = [possible_improvements[answer_length % len(possible_improvements)]]
    
    evaluation = {
        "score": score,
        "strengths": strengths,
        "improvements": improvements,
        "weaknesses": improvements,
        "content": {
            "relevance": min(10, 5 + len(set(request.question.lower().split()).intersection(set(request.answer.lower().split())))),
            "depth": 5 if answer_length > 200 else 3
        },
        "tone": {
            "clarity": 7,
            "professionalism": 8
        },
        "why_asked": "Assesses clarity, relevance to the question, and ability to tailor responses to the role.",
        "feedback": "Your answer demonstrates some strengths. To improve, ensure you directly address the question up front, then use a brief STAR structure and quantify outcomes where possible.",
        "example_improvement": "Provide a concise, structured answer with 1-2 concrete examples and measurable results."
    }
    
    if "answers" not in session:
        session["answers"] = []
    if "evaluations" not in session:
        session["evaluations"] = []
    
    session["answers"].append({"question": request.question, "answer": request.answer})
    session["evaluations"].append(evaluation)
    session["current_question_index"] = len(session["answers"])
    # Update per_question as well (backward compatible)
    questions = session.get("questions") or []
    idx = min(len(session["answers"]) - 1, max(0, len(questions) - 1)) if questions else len(session["answers"]) - 1
    perq = session.get("per_question") or [None] * len(questions)
    if len(perq) < len(questions):
        perq.extend([None] * (len(questions) - len(perq)))
    if questions:
        perq[idx] = evaluation
        session["per_question"] = perq
    _persist_session_state(session_id, session)

    return {"evaluation": evaluation}


@app.post("/generate-example-answer", response_model=ExampleAnswerResponse)
async def generate_example_answer(request: ExampleAnswerRequest):
    session_id = request.session_id
    session = _get_session(session_id)
    # Bind session id into logging context for correlation
    try:
        session_id_var.set(session_id)
    except Exception:
        pass
    log_event(
        "example.request",
        session_id=session_id,
        question_chars=len(request.question or ""),
    )

    for attempt in range(2):
        session = await _ensure_agent_ready(session_id, session, force_restart=attempt > 0)
        agent = session.get("agent")
        if agent is None:
            continue
        try:
            example_answer = await agent.generate_example_answer(request.question)
            log_event(
                "example.agent",
                session_id=session_id,
                attempt=attempt + 1,
            )
            return {"answer": example_answer}
        except Exception:
            log_event(
                "example.agent.error",
                level="exception",
                session_id=session_id,
                attempt=attempt + 1,
            )
            session["agent"] = None
            _persist_session_state(session_id, session)

    log_event("example.fallback", session_id=session_id)
    return {"answer": _example_answer_fallback(request.question)}


@app.get("/session/{session_id}")
async def get_session_status(session_id: str):
    session = _get_session(session_id)

    return {
        "session_id": session_id,
        "name": session.get("name"),
        "coach_persona": session.get("coach_persona", "discovery"),
        "questions": session["questions"],
        "answers": session["answers"],
        "evaluations": session["evaluations"],
        "current_question_index": session.get("current_question_index", 0),
        "voice_transcripts": session.get("voice_transcripts", {}),
        "voice_user_text": session.get("voice_user_text", {}),
        "per_question": session.get("per_question", []),
        "voice_agent_text": session.get("voice_agent_text", {}),
    }


@app.get("/session/{session_id}/documents")
async def get_session_documents(session_id: str):
    """Return stored resume and job description content with basic stats."""
    session = _get_session(session_id)
    try:
        session_id_var.set(session_id)
    except Exception:
        pass
    resume_text = (session.get("resume_text") or "").strip()
    job_desc_text = (session.get("job_desc_text") or "").strip()

    def _payload(text: str) -> Dict[str, Any]:
        """Build a consistent payload describing stored document details."""
        preview_limit = 4000
        preview = text if len(text) <= preview_limit else text[: preview_limit - 3].rstrip() + "..."
        return {
            "present": bool(text),
            "characters": len(text),
            "words": len(text.split()),
            "text": text,
            "preview": preview,
        }

    payload = {
        "session_id": session_id,
        "name": session.get("name"),
        "resume": _payload(resume_text),
        "job_description": _payload(job_desc_text),
    }
    log_event(
        "documents.fetch",
        session_id=session_id,
        resume_chars=len(resume_text),
        job_chars=len(job_desc_text),
        resume_present=bool(resume_text),
        job_present=bool(job_desc_text),
    )
    return payload


@app.post("/session/{session_id}/voice-transcript")
async def save_voice_transcript(session_id: str, payload: SaveTranscriptRequest):
    """Persist voice transcript text for a given question index."""
    session = _get_session(session_id)
    text_value = (payload.text or "").strip()
    vt = session.get("voice_transcripts") or {}
    vt[str(payload.question_index)] = text_value
    session["voice_transcripts"] = vt
    user_map = session.get("voice_user_text") or {}
    user_map[str(payload.question_index)] = text_value
    session["voice_user_text"] = user_map
    _persist_session_state(session_id, session)
    log_event(
        "voice.transcript.user.save",
        session_id=session_id,
        question_index=payload.question_index,
        characters=len(text_value),
        source=(payload.source or "").strip() or None,
    )
    return {"ok": True}


@app.post("/session/{session_id}/voice-agent-text")
async def save_voice_agent_text(session_id: str, payload: SaveAgentTextRequest):
    """Persist the coach's voice text output for a given question index."""
    session = _get_session(session_id)
    vat = session.get("voice_agent_text") or {}
    vat[str(payload.question_index)] = payload.text or ""
    session["voice_agent_text"] = vat
    _persist_session_state(session_id, session)
    preview = (payload.text or "").strip()
    if len(preview) > 160:
        preview = f"{preview[:157].rstrip()}..."
    log_event(
        "voice.coach.save",
        session_id=session_id,
        question_index=payload.question_index,
        characters=len(payload.text or ""),
        preview=preview or None,
    )
    return {"ok": True}


@app.get("/session/{session_id}/voice-transcript/export")
async def export_voice_transcript(session_id: str, format: str = "json"):
    """Export the persisted voice conversation for a session."""
    export_format = (format or "json").strip().lower()
    if export_format != "json":
        raise HTTPException(status_code=415, detail="Only JSON export is supported.")

    session = _get_session(session_id)
    try:
        session_id_var.set(session_id)
    except Exception:
        pass

    user_map = session.get("voice_user_text") or {}
    legacy_map = session.get("voice_transcripts") or {}
    coach_map = session.get("voice_agent_text") or {}
    questions = session.get("questions") or []

    indices: set[int] = set(range(len(questions)))
    for mapping in (user_map, legacy_map, coach_map):
        for raw_key in (mapping or {}).keys():
            try:
                indices.add(int(raw_key))
            except (TypeError, ValueError):
                continue

    entries = []
    for idx in sorted(indices):
        idx_key = str(idx)
        question_text = questions[idx] if idx < len(questions) else None
        candidate_text = (
            (user_map.get(idx_key) or user_map.get(idx)) or
            (legacy_map.get(idx_key) or legacy_map.get(idx)) or
            ""
        )
        coach_text = (coach_map.get(idx_key) or coach_map.get(idx) or "")
        if not any([question_text, candidate_text, coach_text]):
            continue
        entries.append({
            "question_index": idx,
            "question": question_text,
            "candidate_text": candidate_text,
            "coach_text": coach_text,
        })

    payload = {
        "session_id": session_id,
        "name": session.get("name"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "entries": entries,
    }
    log_event(
        "voice.transcript.export",
        session_id=session_id,
        format=export_format,
        entries=len(entries),
    )
    return JSONResponse(content=payload)


def _get_work_history_store():
    """Resolve the preferred knowledge store implementation for the session."""
    try:
        # Ensure directory exists
        KNOWLEDGE_STORE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        log_event("knowledge.store.ensure_error", level="exception")
    try:
        return get_work_history_store(WORK_HISTORY_STORE_FILE)
    except Exception as e:
        # Fallback to lexical store if FAISS/embeddings unavailable
        log_event("knowledge.store.fallback", level="exception", error=str(e))
        try:
            from app.utils.vector_store import get_work_history_store as get_lex
            return get_lex(WORK_HISTORY_STORE_FILE)
        except Exception:
            raise


@app.get("/work-history")
async def work_history_stats():
    """Return stats for the local work-history knowledge store."""
    store = _get_work_history_store()
    stats = store.stats()
    log_event(
        "knowledge.stats",
        engine=stats.get("engine"),
        docs=stats.get("docs"),
        dim=stats.get("dim"),
        model=stats.get("model"),
    )
    return stats


@app.post("/work-history/add")
async def work_history_add(req: WorkHistoryAddRequest):
    """Add chunks into the work-history knowledge store."""
    store = _get_work_history_store()
    texts = [c.text for c in req.chunks]
    metas = [(c.metadata or {}) for c in req.chunks]
    try:
        added = store.add_texts(texts, metas)
    except Exception as e:
        msg = str(e)
        if "OpenAI client not configured" in msg or "embeddings" in msg.lower():
            raise HTTPException(status_code=400, detail="Embeddings unavailable. Set OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL.")
        raise
    stats = store.stats()
    log_event("knowledge.add", added=added, total_docs=stats.get("docs"))
    return {"added": added, "stats": stats}


@app.post("/work-history/import-path")
async def work_history_import_path(req: WorkHistoryImportPathRequest):
    """Import chunked data from a local file or directory path.

    - Supports .txt/.md (blank-line paragraphs), .jsonl (per-line JSON with 'text'/'content'), and .json (array or {chunks: [...]})
    """
    p = (req.path or "").strip()
    if not p:
        raise HTTPException(status_code=400, detail="Path must be provided")
    sanitized_path: Path
    try:
        sanitized_path = _resolve_import_path(p)
    except HTTPException:
        raise
    except Exception:
        log_event("knowledge.import.resolve_error", level="exception", path=p)
        raise HTTPException(status_code=400, detail="Invalid path")

    store = _get_work_history_store()
    try:
        log_event("knowledge.import.start", path=str(sanitized_path))
        added = store.import_path(sanitized_path)
        log_event("knowledge.import.end", path=str(sanitized_path), added=added)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Path not found")
    except Exception as e:
        log_event("knowledge.import.error", level="exception", path=str(sanitized_path))
        msg = str(e)
        if "OpenAI client not configured" in msg or "embeddings" in msg.lower():
            raise HTTPException(status_code=400, detail="Embeddings unavailable. Set OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL.")
        raise HTTPException(status_code=500, detail="Failed to import from path")
    return {"imported": added, "stats": store.stats()}


@app.get("/work-history/search")
async def work_history_search(q: str, k: int = 5):
    """Search work-history knowledge store for relevant snippets."""
    store = _get_work_history_store()
    try:
        log_event("knowledge.search.api.start", query=q, k=k)
        results = store.search(q, k=k)
        log_event("knowledge.search.api.end", query=q, results=len(results))
    except Exception as e:
        msg = str(e)
        if "OpenAI client not configured" in msg or "embeddings" in msg.lower():
            raise HTTPException(status_code=400, detail="Embeddings unavailable. Set OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL.")
        raise
    # Return safe, trimmed payload
    def trim(t: str, n: int = 400) -> str:
        """Trim snippets to a safe preview length for the API response."""
        t = t or ""
        return t if len(t) <= n else t[: n - 3] + "..."
    payload = [
        {
            "id": r.get("id"),
            "score": r.get("score"),
            "snippet": trim(r.get("text") or ""),
            "metadata": r.get("metadata") or {},
        }
        for r in results
    ]
    return {"results": payload}


@app.delete("/work-history")
async def work_history_clear():
    """Clear the work-history knowledge store."""
    store = _get_work_history_store()
    store.clear()
    log_event("knowledge.clear")
    return {"ok": True}


@app.post("/session/{session_id}/voice-transcript/memorize")
async def memorize_voice_transcript(session_id: str, req: MemorizeTranscriptRequest):
    """Save a voice transcript (raw or summarized) into the work-history store.

    - If `text` is provided, uses it directly.
    - Else if `question_index` is provided, uses the persisted transcript for that index.
    - When `summarize` is true, it generates a concise STAR-style snippet before saving.
    """
    session = _get_session(session_id)
    user_map = session.get("voice_user_text") or {}
    vt_map = session.get("voice_transcripts") or {}
    combined_map = {**{str(k): v for k, v in vt_map.items()}, **{str(k): v for k, v in user_map.items()}}
    qidx = req.question_index
    text = (req.text or "").strip()
    if not text:
        if qidx is None:
            raise HTTPException(status_code=400, detail="Provide text or question_index")
        text = (combined_map.get(str(qidx)) or combined_map.get(qidx) or "").strip()
        if not text:
            raise HTTPException(status_code=404, detail="No transcript found for that index")

    # Optionally summarize to a compact, reusable snippet
    snippet = text
    if req.summarize:
        try:
            base = get_base_coach_prompt()
            system = f"{base}\n\nYou will compress a spoken answer into a crisp STAR+I summary with concrete metrics (80–180 words)."
            user = f"Question: {(session.get('questions') or [''])[qidx] if (qidx is not None) else ''}\n\nSpoken answer transcript:\n{text}\n\nSummarize succinctly as a reusable accomplishment bullet."
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            resp = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            snippet = (resp.choices[0].message.content or "").strip() or text
        except Exception:
            log_event("knowledge.memorize.summarize.error", level="exception", session_id=session_id)
            # Fall back to raw transcript
            snippet = text

    meta = dict(req.metadata or {})
    meta.update({
        "session_id": session_id,
        "question_index": qidx,
        "question": ((session.get("questions") or [None])[qidx] if (qidx is not None) else None),
        "source": "voice_memorize",
        "created_at": datetime.utcnow().isoformat() + "Z",
    })

    store = _get_work_history_store()
    log_event(
        "knowledge.memorize.start",
        session_id=session_id,
        question_index=qidx,
        summarize=req.summarize,
    )
    added = 0
    try:
        added = store.add_texts([snippet], [meta])
    except Exception as e:
        msg = str(e)
        if "OpenAI client not configured" in msg or "embeddings" in msg.lower():
            raise HTTPException(status_code=400, detail="Embeddings unavailable. Set OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL.")
        raise
    stats = store.stats()
    log_event(
        "knowledge.memorize.end",
        session_id=session_id,
        added=added,
        total_docs=stats.get("docs"),
    )
    return {"added": added, "snippet": snippet, "stats": stats}

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session = _get_session(session_id)
    log_event("session.delete.request", session_id=session_id)

    try:
        os.remove(session["resume_path"])
        os.remove(session["job_desc_path"])
    except Exception:
        log_event("session.delete.cleanup_error", level="exception", session_id=session_id)
    
    active_sessions.pop(session_id, None)
    delete_persisted_session(session_id)
    log_event("session.delete.success", session_id=session_id)
    
    return {"message": "Session deleted successfully"}


@app.get("/sessions", response_model=List[SessionListItem])
async def list_sessions():
    items = list_persisted_sessions()
    log_event("session.list", count=len(items))
    return items


@app.patch("/session/{session_id}/name")
async def rename_session(session_id: str, request: RenameSessionRequest):
    """Rename a saved session and persist the change."""
    session = _get_session(session_id)
    new_name = (request.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name must not be empty")

    session["name"] = new_name
    _persist_session_state(session_id, session)
    log_event("session.rename", session_id=session_id, name=new_name)

    updated = rename_persisted_session(session_id, new_name)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "name": new_name}


@app.patch("/session/{session_id}/coach")
async def set_coach_persona(session_id: str, request: SetCoachPersonaRequest):
    """Set the coach persona for a session: ruthless | helpful | discovery."""
    session = _get_session(session_id)
    requested_persona = (request.persona or "").strip().lower()
    current_persona = (session.get("coach_persona") or "discovery").lower()
    current_display = _coach_display_name(current_persona)
    if requested_persona not in {"ruthless", "helpful", "discovery"}:
        log_event(
            "persona.update.invalid",
            level="warning",
            session_id=session_id,
            persona=requested_persona or None,
            previous_persona=current_persona,
            coach=current_display,
        )
        raise HTTPException(status_code=400, detail="Invalid persona. Use ruthless, helpful, or discovery.")
    previous_persona = session.get("coach_persona", "discovery")
    if requested_persona == current_persona:
        log_event(
            "persona.update.noop",
            session_id=session_id,
            persona=requested_persona,
            coach=current_display,
        )
        return {"session_id": session_id, "coach_persona": requested_persona}
    session["coach_persona"] = requested_persona
    _persist_session_state(session_id, session)
    log_event(
        "persona.update",
        session_id=session_id,
        persona=requested_persona,
        previous_persona=previous_persona,
        coach=_coach_display_name(requested_persona),
    )
    # If an agent exists, update it in-place
    try:
        agent = session.get("agent")
        if agent is not None:
            agent.persona = requested_persona
    except Exception:
        pass
    return {"session_id": session_id, "coach_persona": requested_persona}


def _truncate_text(text: str, limit: int = 1200) -> str:
    """Return a trimmed preview of longer text snippets."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _voice_question_plan(session: Dict[str, Any]) -> tuple[str, str]:
    """Derive the first question and bullet list used in voice prompts."""
    questions: List[str] = session.get("questions") or []
    first_question = questions[0] if questions else "Tell me about yourself."
    bullets = "\n".join(f"- {q}" for q in questions[:5]) or "- Ask situational and behavioral questions tailored to the role."
    return first_question, bullets


def _voice_document_excerpts(session: Dict[str, Any]) -> tuple[str, str]:
    """Collect truncated resume and job description excerpts."""
    resume_excerpt = _truncate_text(session.get("resume_text", ""), 1500)
    job_desc_excerpt = _truncate_text(session.get("job_desc_text", ""), 1500)
    return resume_excerpt, job_desc_excerpt


def _voice_persona_slug(session: Dict[str, Any], persona: Optional[str]) -> str:
    """Resolve the persona slug for the voice prompt."""
    return (persona or session.get("coach_persona") or "discovery").lower()


def _voice_agent_name_line(agent_name: Optional[str]) -> str:
    """Provide the persona-aware agent introduction line."""
    return f"You are the interview coach named '{(agent_name or 'Coach')}'.".strip()


def _collect_work_history_snippets(session_id: str, query: str) -> List[str]:
    """Fetch relevant work-history snippets, logging telemetry for visibility."""
    snippets: List[str] = []
    try:
        store = _get_work_history_store()
        log_event("knowledge.search.start", session_id=session_id, query=query)
        results = store.search(query, k=5)
        log_event("knowledge.search.end", session_id=session_id, matches=len(results))
        for record in results:
            snippet = _truncate_text(record.get("text") or "", 240)
            if snippet:
                snippets.append(f"- {snippet}")
    except Exception:
        log_event("knowledge.search.error", level="exception", session_id=session_id)
    return snippets


def _build_voice_instructions(session_id: str, session: Dict[str, Any], agent_name: Optional[str] = None, persona: Optional[str] = None) -> str:
    """Create instructions for the realtime voice agent based on session context.

    Prepends the same system-level coach persona used by the text agent to
    keep behavior consistent across text and voice.
    """
    first_question, question_bullets = _voice_question_plan(session)
    resume_excerpt, job_desc_excerpt = _voice_document_excerpts(session)
    persona_slug = _voice_persona_slug(session, persona)
    base_prompt = get_voice_system_prompt(persona_slug)
    name_line = _voice_agent_name_line(agent_name)

    query = first_question or "Interview practice"
    snippets = _collect_work_history_snippets(session_id, query)
    snippets_block = "\n".join(snippets) if snippets else "- (No stored work-history snippets found)"

    instructions = f"""
{base_prompt}

# Realtime Voice Context (session {session_id}):
{name_line}
Candidate resume excerpt:
{resume_excerpt}

Job description excerpt:
{job_desc_excerpt}

Interview question plan:
{question_bullets}

# Work History Knowledge Pool (top matches):
{snippets_block}

# Realtime Guidance:
Conduct a conversational mock interview. Start with a brief greeting, then ask the first question exactly as "{first_question}".
Listen to the candidate's voice response. After they finish, provide concise, constructive feedback and practical tips (under 4 sentences).
Proceed through the remaining questions naturally. If the candidate asks for clarification or coaching, offer targeted guidance.
Keep responses under 30 seconds and always send a short text summary alongside audio so the UI can display the feedback.
Wrap up when the candidate indicates they are done or when the planned questions are covered.

If the candidate says a phrase like "remember that" or "please remember this", briefly acknowledge that it will be saved to their knowledge pool. The app will persist the note; keep your acknowledgement short (e.g., "Got it — I’ll remember that.").
"""
    return textwrap.dedent(instructions).strip()


@app.post("/voice/session", response_model=VoiceSessionResponse)
async def create_voice_session(request: VoiceSessionRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key is not configured")

    session = _get_session(request.session_id)
    voice_name = request.voice or OPENAI_REALTIME_VOICE
    persona = (request.persona or session.get("coach_persona") or "discovery").lower()
    instructions = _build_voice_instructions(request.session_id, session, request.agent_name, persona)
    try:
        session_id_var.set(request.session_id)
    except Exception:
        pass
    log_event(
        "voice.session.create.start",
        session_id=request.session_id,
        persona=persona,
        voice=voice_name,
        agent_name=request.agent_name or session.get("agent_name"),
        coach=_coach_display_name(persona),
    )

    payload: Dict[str, Any] = {
        "model": OPENAI_REALTIME_MODEL,
        "modalities": ["audio", "text"],
        "voice": voice_name,
        "instructions": instructions,
    }

    transcription_model = (OPENAI_INPUT_TRANSCRIPTION_MODEL or "").strip()
    if transcription_model:
        payload["input_audio_transcription"] = {
            "model": transcription_model,
            "language": "en",
        }

    # Optional server-side VAD (turn detection) configuration
    try:
        td_mode = (OPENAI_TURN_DETECTION or "server_vad").strip().lower()
        if td_mode == "none":
            payload["turn_detection"] = {"type": "none"}
        else:
            threshold = float(OPENAI_TURN_THRESHOLD)
            prefix_ms = int(OPENAI_TURN_PREFIX_MS)
            silence_ms = int(OPENAI_TURN_SILENCE_MS)
            payload["turn_detection"] = {
                "type": "server_vad",
                "threshold": threshold,
                "prefix_padding_ms": prefix_ms,
                "silence_duration_ms": silence_ms,
            }
    except Exception:
        # If parsing fails, fall back silently without turn_detection overrides
        log_event(
            "voice.session.vad_error",
            level="exception",
            session_id=request.session_id,
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                    "OpenAI-Beta": "realtime=v1",
                },
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = "Unable to start realtime voice session"
        error_payload: Optional[str]
        try:
            error_payload = exc.response.text
        except Exception:
            error_payload = None
        log_event(
            "voice.session.create.error",
            level="exception",
            session_id=request.session_id,
            status=exc.response.status_code,
            error=error_payload,
        )
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.HTTPError:
        log_event(
            "voice.session.create.transport_error",
            level="exception",
            session_id=request.session_id,
        )
        raise HTTPException(status_code=502, detail="Realtime voice service unavailable")

    data = response.json()
    client_secret = data.get("client_secret", {}).get("value")
    if not client_secret:
        log_event(
            "voice.session.create.missing_secret",
            level="error",
            session_id=request.session_id,
        )
        raise HTTPException(status_code=500, detail="Realtime voice session unavailable")

    log_event(
        "voice.session.create.success",
        session_id=request.session_id,
        voice=voice_name,
        model=data.get("model", OPENAI_REALTIME_MODEL),
        agent_name=request.agent_name or session.get("agent_name"),
        persona=persona,
        coach=_coach_display_name(persona),
    )

    return VoiceSessionResponse(
        id=data.get("id", ""),
        model=data.get("model", OPENAI_REALTIME_MODEL),
        client_secret=client_secret,
        url=OPENAI_REALTIME_URL,
        expires_at=data.get("expires_at"),
    )


# Helper functions
async def start_agent(session_id: str):
    """Start the interview agent for a session."""
    try:
        session_id_var.set(session_id)
    except Exception:
        pass
    session = active_sessions.get(session_id)
    if session is None:
        stored = load_persisted_session(session_id)
        if stored is None:
            log_event("agent.start.missing_session", level="warning", session_id=session_id)
            return
        session = stored
        active_sessions[session_id] = session

    if session.get("agent") is not None:
        log_event("agent.start.cached", level="debug", session_id=session_id)
        return

    try:
        # Initialize the agent with session data
        config = InterviewAgentConfig(
            openai_api_key=OPENAI_API_KEY,
            openai_model=OPENAI_MODEL,
            resume_text=session["resume_text"],
            job_description_text=session["job_desc_text"],
            session_id=session_id,
            persona=session.get("coach_persona", "discovery"),
        )
        agent = InterviewPracticeAgent(config)

        # Start the agent
        await agent.start()

        # Store the agent in the session
        session["agent"] = agent
        _persist_session_state(session_id, session)

        log_event("agent.start.success", session_id=session_id)
    except Exception:
        log_event("agent.start.error", level="exception", session_id=session_id)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "app.unhandled_error",
        extra={
            "method": request.method,
            "path": request.url.path,
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
