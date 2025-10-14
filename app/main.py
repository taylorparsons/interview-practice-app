import logging
import os
import asyncio
import textwrap
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from functools import lru_cache
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request
import httpx
import uvicorn

# Import local modules
from app.config import (
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_REALTIME_MODEL,
    OPENAI_REALTIME_VOICE, OPENAI_REALTIME_URL,
    OPENAI_TURN_DETECTION, OPENAI_TURN_THRESHOLD, OPENAI_TURN_PREFIX_MS, OPENAI_TURN_SILENCE_MS,
    OPENAI_INPUT_TRANSCRIPTION_MODEL,
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS,
    VOICE_BROWSER_FALLBACK_DEFAULT, VOICE_SHOW_METADATA_DEFAULT,
)
from app.utils.document_processor import allowed_file, save_uploaded_file, save_text_as_file, process_documents
from app.models.interview_agent import InterviewPracticeAgent, get_base_coach_prompt
from app.models.prompts import build_dual_level_prompt
from app.logging_config import setup_logging
from app.logging_context import session_id_var
from app.middleware.request_logging import RequestLoggingMiddleware
from app.utils.session_store import (
    save_session as persist_session,
    load_session as load_persisted_session,
    delete_session as delete_persisted_session,
    list_sessions as list_persisted_sessions,
    rename_session as rename_persisted_session,
)

setup_logging()
logger = logging.getLogger(__name__)

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


def _get_session(session_id: str) -> Dict[str, Any]:
    """Retrieve a session from memory or disk, raising 404 when missing."""
    session = active_sessions.get(session_id)
    if session is not None:
        return _ensure_session_defaults(session)

    stored = load_persisted_session(session_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _ensure_session_defaults(stored)
    active_sessions[session_id] = session
    return session


def _ensure_session_defaults(session: Dict[str, Any]) -> Dict[str, Any]:
    """Populate expected session collections when missing."""
    if "voice_transcripts" not in session or session["voice_transcripts"] is None:
        session["voice_transcripts"] = {}
    if "voice_agent_text" not in session or session["voice_agent_text"] is None:
        session["voice_agent_text"] = {}
    if "voice_messages" not in session or session["voice_messages"] is None:
        session["voice_messages"] = []
    if "voice_settings" not in session or session["voice_settings"] is None:
        session["voice_settings"] = {}
    # Default the coaching persona to the easier (supportive) mode when
    # missing. This value is persisted per-session and can be changed by the UI
    # via PATCH /session/{id}/coach-level.
    if "coach_level" not in session or not session.get("coach_level"):
        session["coach_level"] = "level_1"
    return session


def _persist_session_state(session_id: str, session: Dict[str, Any]) -> None:
    """Update the in-memory cache and persist session state to disk."""
    active_sessions[session_id] = session
    persist_session(session_id, session)


async def _ensure_agent_ready(session_id: str, session: Dict[str, Any], *, force_restart: bool = False) -> Dict[str, Any]:
    """Ensure an agent is ready for the session, optionally forcing a restart."""
    if force_restart and session.get("agent") is not None:
        logger.info("agent.ensure.reset: session=%s", session_id)
        session["agent"] = None
        _persist_session_state(session_id, session)

    if session.get("agent") is None:
        logger.info("agent.ensure.start: session=%s", session_id)
        try:
            await start_agent(session_id)
        except Exception:
            logger.exception("agent.ensure.error: session=%s", session_id)
        session = _get_session(session_id)
        if session.get("agent") is None:
            logger.warning("agent.ensure.unavailable: session=%s", session_id)
        else:
            logger.info("agent.ensure.ready: session=%s", session_id)

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
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s or "item"

    return f"{slugify(title)}_{slugify(company)}"


# Request and response models
class DocumentUploadResponse(BaseModel):
    session_id: str
    message: str
    name: Optional[str] = None


class GenerateQuestionsRequest(BaseModel):
    session_id: str
    num_questions: int = 5


class GenerateQuestionsResponse(BaseModel):
    questions: List[str]


class EvaluateAnswerRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    voice_transcript: Optional[str] = None


class EvaluateAnswerResponse(BaseModel):
    evaluation: Dict[str, Any]


class ExampleAnswerRequest(BaseModel):
    session_id: str
    question: str


class ExampleAnswerResponse(BaseModel):
    answer: str


class VoiceSessionRequest(BaseModel):
    session_id: str
    voice: Optional[str] = None


class VoiceSessionResponse(BaseModel):
    id: str
    model: str
    client_secret: str
    url: str
    expires_at: Optional[int] = None


class VoiceDescriptor(BaseModel):
    id: str
    label: str
    preview_url: Optional[str] = None


class SessionListItem(BaseModel):
    id: str
    name: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    questions_count: Optional[int] = 0
    answers_count: Optional[int] = 0


class RenameSessionRequest(BaseModel):
    name: str


class SaveTranscriptRequest(BaseModel):
    question_index: int
    text: str


class SaveAgentTextRequest(BaseModel):
    question_index: int
    text: str


class VoiceMessagePayload(BaseModel):
    role: str
    text: str
    timestamp: Optional[str] = None
    stream: Optional[bool] = False
    question_index: Optional[int] = None


class SetCoachLevelRequest(BaseModel):
    level: str


# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "voice_browser_fallback_default": VOICE_BROWSER_FALLBACK_DEFAULT,
            "voice_show_metadata_default": VOICE_SHOW_METADATA_DEFAULT,
        },
    )


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
        "questions": [],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "voice_transcripts": {},
        "voice_agent_text": {},
        "voice_messages": [],
        # Store the UI-selectable coach level; default to level_1 (Help).
        "coach_level": "level_1",
    }

    _persist_session_state(session_id, session_data)
    
    # Initialize and start the agent in the background
    if background_tasks:
        background_tasks.add_task(start_agent, session_id)
    
    return {"session_id": session_id, "message": "Documents uploaded successfully", "name": default_name}


@app.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    session_id = request.session_id
    session = _get_session(session_id)

    if session.get("agent") is not None:
        try:
            agent = session["agent"]
            questions = await agent.generate_interview_questions(request.num_questions)

            session["questions"] = questions
            session["current_question_index"] = 0
            _persist_session_state(session_id, session)

            return {"questions": questions}
        except Exception:
            logger.exception("Error using agent to generate questions for session %s", session_id)

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
                transcripts = session.get("voice_transcripts", {})
                transcript_text = transcripts.get(str(idx)) or transcripts.get(idx) or ""

            logger.info(
                "evaluation.agent path: session=%s attempt=%s idx=%s q_len=%s a_len=%s t_present=%s",
                session_id,
                attempt + 1,
                idx,
                len(request.question or ""),
                len(request.answer or ""),
                bool(transcript_text and transcript_text.strip()),
            )
            evaluation = await agent.evaluate_answer(
                request.question,
                request.answer,
                transcript_text,
                level=session.get("coach_level") or "level_2",
            )

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

            return {"evaluation": evaluation}
        except Exception:
            logger.exception(
                "evaluation.agent error: session=%s attempt=%s", session_id, attempt + 1
            )
            # Drop the agent so a subsequent attempt can reinitialize
            session["agent"] = None
            _persist_session_state(session_id, session)
    
    logger.info(
        "evaluation.fallback path: session=%s q_len=%s a_len=%s",
        session_id,
        len(request.question or ""),
        len(request.answer or ""),
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

    for attempt in range(2):
        session = await _ensure_agent_ready(session_id, session, force_restart=attempt > 0)
        agent = session.get("agent")
        if agent is None:
            continue
        try:
            example_answer = await agent.generate_example_answer(request.question)
            logger.info("example.agent path: session=%s attempt=%s", session_id, attempt + 1)
            return {"answer": example_answer}
        except Exception:
            logger.exception("example.agent error: session=%s attempt=%s", session_id, attempt + 1)
            session["agent"] = None
            _persist_session_state(session_id, session)
    
    question = request.question.lower()
    logger.info("example.fallback path: session=%s", session_id)
    
    if "experience" in question or "background" in question:
        answer = """I have over 5 years of experience in software development with a focus on full-stack web applications. My background includes working at both startups and established companies where I've contributed to all stages of the software development lifecycle. In my most recent role at TechCorp, I led the development of a customer-facing portal that increased customer engagement by 35% and reduced support tickets by 20%. Prior to that, I worked at InnovateX where I built RESTful APIs that improved system performance by 40%. My technical expertise includes JavaScript/TypeScript, React, Node.js, Python, and SQL databases."""
    
    elif "strengths" in question:
        answer = """My greatest professional strengths include technical problem-solving, effective communication, and adaptive learning. When faced with complex technical challenges, I methodically break them down into manageable components and systematically address each one. This approach helped me resolve a critical performance bottleneck in our production system that had been affecting users for weeks. Additionally, I excel at communicating technical concepts to non-technical stakeholders, which has been valuable when working with product managers and business teams. Lastly, I prioritize continuous learning to stay current with emerging technologies and best practices, regularly dedicating time to explore new tools and techniques that could benefit our projects."""
    
    elif "weaknesses" in question:
        answer = """One area I've been working to improve is delegating responsibilities more effectively. In the past, I would take on too many tasks myself, which sometimes led to burnout. I've addressed this by implementing a structured approach to task management and team coordination, focusing on identifying team members' strengths and aligning tasks accordingly. I've also been working on balancing technical perfectionism with practical deadlines, recognizing when something is 'good enough' for an initial release versus when perfection is truly necessary. Through regular feedback and reflection, I've made significant progress in both areas, which has improved both my productivity and work-life balance."""
    
    elif "interest" in question or "why" in question:
        answer = """I'm particularly interested in this position because it aligns perfectly with my technical skills and career aspirations. The opportunity to work on innovative solutions that directly impact users is exciting to me. I've been following your company's growth and am impressed by your commitment to both technical excellence and user experience. The job description mentioned responsibilities around optimizing application performance and implementing new features, which are areas where I have demonstrated success in previous roles. Additionally, your company culture of continuous learning and collaborative problem-solving resonates with my personal work values. I believe my background in similar technologies and experience solving comparable challenges would allow me to make meaningful contributions quickly."""
    
    elif "five years" in question or "future" in question:
        answer = """In five years, I envision myself having deepened my technical expertise while also growing my leadership skills. I aim to become a senior developer who not only contributes high-quality code but also mentors junior team members and influences technical decisions. I'm particularly interested in continuing to specialize in distributed systems while gaining more experience with cloud architecture and scalability challenges. I also plan to further develop my project management skills to potentially move into a technical lead role where I can help bridge the gap between technical implementation and business objectives. Throughout this journey, I'll remain committed to continuous learning and staying current with emerging technologies and methodologies."""
    
    else:
        answer = """Based on my experience and qualifications, I would approach this by leveraging my technical skills and domain knowledge. I believe in combining theoretical understanding with practical implementation, always focusing on delivering value while maintaining code quality and system performance. When facing challenges in this area, I rely on systematic problem-solving, collaboration with team members, and staying current with industry best practices. In my previous roles, I've successfully handled similar situations by breaking down complex problems into manageable components, prioritizing user needs, and implementing solutions that are both robust and scalable. I'm always eager to learn and adapt, which I believe is essential in our rapidly evolving field."""
    
    return {"answer": answer}


@app.get("/session/{session_id}")
async def get_session_status(session_id: str):
    session = _get_session(session_id)

    return {
        "session_id": session_id,
        "name": session.get("name"),
        "questions": session["questions"],
        "answers": session["answers"],
        "evaluations": session["evaluations"],
        "current_question_index": session.get("current_question_index", 0),
        "voice_transcripts": session.get("voice_transcripts", {}),
        "per_question": session.get("per_question", []),
        "voice_agent_text": session.get("voice_agent_text", {}),
        "voice_messages": session.get("voice_messages", []),
        "voice_settings": session.get("voice_settings", {}),
        # Expose the current coach level to hydrate the UI selector.
        "coach_level": session.get("coach_level", "level_1"),
    }


@app.get("/session/{session_id}/documents")
async def get_session_documents(session_id: str):
    """Return raw resume and job description texts for a session."""
    session = _get_session(session_id)
    return {
        "session_id": session_id,
        "name": session.get("name"),
        "resume_text": session.get("resume_text", ""),
        "job_desc_text": session.get("job_desc_text", ""),
    }


@app.post("/session/{session_id}/voice-transcript")
async def save_voice_transcript(session_id: str, payload: SaveTranscriptRequest):
    """Persist voice transcript text for a given question index."""
    session = _get_session(session_id)
    vt = session.get("voice_transcripts") or {}
    vt[str(payload.question_index)] = payload.text or ""
    session["voice_transcripts"] = vt
    _persist_session_state(session_id, session)
    return {"ok": True}


@app.post("/session/{session_id}/voice-agent-text")
async def save_voice_agent_text(session_id: str, payload: SaveAgentTextRequest):
    """Persist the coach's voice text output for a given question index."""
    session = _get_session(session_id)
    vat = session.get("voice_agent_text") or {}
    vat[str(payload.question_index)] = payload.text or ""
    session["voice_agent_text"] = vat
    _persist_session_state(session_id, session)
    return {"ok": True}


@app.post("/session/{session_id}/voice-messages")
async def append_voice_message(session_id: str, payload: VoiceMessagePayload):
    """Append a realtime voice message (candidate or coach) to session history."""
    session = _get_session(session_id)

    text = (payload.text or "").strip()
    if not text:
        return {"ok": False, "reason": "empty_text"}

    role_raw = (payload.role or "system").strip().lower()
    role_map = {
        "user": "candidate",
        "candidate": "candidate",
        "coach": "coach",
        "assistant": "coach",
        "agent": "coach",
        "system": "system",
    }
    normalized_role = role_map.get(role_raw, role_raw or "system")

    entry: Dict[str, Any] = {
        "role": normalized_role,
        "text": text,
        "timestamp": payload.timestamp or datetime.utcnow().isoformat() + "Z",
    }
    if payload.stream is not None:
        entry["stream"] = bool(payload.stream)
    if payload.question_index is not None:
        entry["question_index"] = payload.question_index

    messages = session.get("voice_messages") or []
    messages.append(entry)
    session["voice_messages"] = messages

    q_index = payload.question_index
    if q_index is not None:
        key = str(q_index)
        if normalized_role == "candidate":
            vt = session.get("voice_transcripts") or {}
            existing = (vt.get(key) or "").strip()
            vt[key] = f"{existing}\n{text}".strip() if existing else text
            session["voice_transcripts"] = vt
        elif normalized_role == "coach":
            vat = session.get("voice_agent_text") or {}
            existing = (vat.get(key) or "").strip()
            vat[key] = f"{existing}\n{text}".strip() if existing else text
            session["voice_agent_text"] = vat

    _persist_session_state(session_id, session)
    candidate_count = sum(1 for m in messages if m.get("role") == "candidate")
    coach_count = sum(1 for m in messages if m.get("role") == "coach")
    completeness = bool(candidate_count and coach_count)
    logger.info(
        "voice.transcript.metric: session=%s role=%s idx=%s total=%s candidate_count=%s coach_count=%s complete=%s",
        session_id,
        normalized_role,
        q_index,
        len(messages),
        candidate_count,
        coach_count,
        completeness,
    )
    logger.debug(
        "voice.message.appended: session=%s role=%s idx=%s total=%s",
        session_id,
        normalized_role,
        q_index,
        len(messages),
    )
    return {"ok": True, "index": len(messages) - 1}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session = _get_session(session_id)

    try:
        os.remove(session["resume_path"])
        os.remove(session["job_desc_path"])
    except Exception:
        logger.exception("Error cleaning up files for session %s", session_id)
    
    active_sessions.pop(session_id, None)
    delete_persisted_session(session_id)
    
    return {"message": "Session deleted successfully"}


@app.get("/sessions", response_model=List[SessionListItem])
async def list_sessions():
    """List all saved sessions with basic metadata."""
    items = list_persisted_sessions()
    return [SessionListItem(**item) for item in items]


@app.patch("/session/{session_id}/name")
async def rename_session(session_id: str, request: RenameSessionRequest):
    """Rename a saved session and persist the change."""
    session = _get_session(session_id)
    new_name = (request.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name must not be empty")

    session["name"] = new_name
    _persist_session_state(session_id, session)

    updated = rename_persisted_session(session_id, new_name)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "name": new_name}


def _truncate_text(text: str, limit: int = 1200) -> str:
    """Return a trimmed preview of longer text snippets."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _build_voice_instructions(session_id: str, session: Dict[str, Any]) -> str:
    """Create instructions for the realtime voice agent based on session context.

    Prepends the same system-level coach persona used by the text agent to
    keep behavior consistent across text and voice.
    """
    questions: List[str] = session.get("questions") or []
    first_question = questions[0] if questions else "Tell me about yourself."
    question_bullets = "\n".join(f"- {q}" for q in questions[:5]) or "- Ask situational and behavioral questions tailored to the role."
    resume_excerpt = _truncate_text(session.get("resume_text", ""), 1500)
    job_desc_excerpt = _truncate_text(session.get("job_desc_text", ""), 1500)

    # Build the system prompt using the selected coach persona.
    level = session.get("coach_level") or "level_1"
    base_prompt = build_dual_level_prompt(level)

    instructions = f"""
{base_prompt}

# Realtime Voice Context (session {session_id}):
Candidate resume excerpt:
{resume_excerpt}

Job description excerpt:
{job_desc_excerpt}

Interview question plan:
{question_bullets}

# Realtime Guidance:
Conduct a conversational mock interview. Start with a brief greeting, then ask the first question exactly as "{first_question}".
Listen to the candidate's voice response. After they finish, provide concise, constructive feedback and practical tips (under 4 sentences).
Proceed through the remaining questions naturally. If the candidate asks for clarification or coaching, offer targeted guidance.
Keep responses under 30 seconds and always send a short text summary alongside audio so the UI can display the feedback.
Wrap up when the candidate indicates they are done or when the planned questions are covered.
"""
    return textwrap.dedent(instructions).strip()


@app.patch("/session/{session_id}/coach-level")
async def set_coach_level(session_id: str, payload: SetCoachLevelRequest):
    """Update the coaching level used by prompts and realtime instructions."""
    session = _get_session(session_id)
    level = (payload.level or "").strip().lower()
    if level not in {"level_1", "level_2"}:
        raise HTTPException(status_code=400, detail="Invalid level; use level_1 or level_2")
    old = session.get("coach_level") or "level_1"
    session["coach_level"] = level
    _persist_session_state(session_id, session)
    # Emit structured info for telemetry and auditing of coach-level changes
    try:
        logger.info("coach.level.change: session=%s from=%s to=%s", session_id, old, level)
    except Exception:
        pass
    return {"ok": True, "level": level}


@app.post("/voice/session", response_model=VoiceSessionResponse)
async def create_voice_session(request: VoiceSessionRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key is not configured")

    session = _get_session(request.session_id)
    # Determine voice selection precedence: session settings > request override > default
    selected_voice = None
    try:
        selected_voice = (session.get("voice_settings") or {}).get("voice_id")
    except Exception:
        selected_voice = None
    voice_name = selected_voice or request.voice or OPENAI_REALTIME_VOICE
    instructions = _build_voice_instructions(request.session_id, session)

    payload: Dict[str, Any] = {
        "model": OPENAI_REALTIME_MODEL,
        "modalities": ["audio", "text"],
        "voice": voice_name,
        "instructions": instructions,
    }

    # Enable server-side speech-to-text so user utterances arrive as transcript events
    if OPENAI_INPUT_TRANSCRIPTION_MODEL:
        payload["input_audio_transcription"] = {"model": OPENAI_INPUT_TRANSCRIPTION_MODEL}

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
        logger.exception("Invalid VAD configuration; proceeding with service defaults")

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
        logger.exception(
            "Realtime session creation failed with status %s: %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.HTTPError:
        logger.exception("Error contacting OpenAI realtime API")
        raise HTTPException(status_code=502, detail="Realtime voice service unavailable")

    data = response.json()
    client_secret = data.get("client_secret", {}).get("value")
    if not client_secret:
        logger.error("Realtime session response missing client secret: %s", data)
        raise HTTPException(status_code=500, detail="Realtime voice session unavailable")

    return VoiceSessionResponse(
        id=data.get("id", ""),
        model=data.get("model", OPENAI_REALTIME_MODEL),
        client_secret=client_secret,
        url=OPENAI_REALTIME_URL,
        expires_at=data.get("expires_at"),
    )


@lru_cache(maxsize=4)
def _load_voice_catalog(_version: float) -> List[Dict[str, Any]]:
    """Load static voice catalog from JSON file.

    The `_version` parameter should pass the file's last-modified time so that
    updates to `voice_catalog.json` are reflected without restarting the server
    and without permanently disabling caching.
    """
    path = os.path.join(os.path.dirname(__file__), "voice_catalog.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            import json as _json

            data = _json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        logger.exception("Failed to load voice catalog from %s", path)
    return []


@app.get("/voices", response_model=List[VoiceDescriptor])
async def list_voices():
    """Return the available voice catalog for selection and preview.

    Includes a lightweight cache that invalidates when the JSON file changes.
    """
    path = os.path.join(os.path.dirname(__file__), "voice_catalog.json")
    try:
        version = os.path.getmtime(path)
    except Exception:
        version = 0.0
    raw = _load_voice_catalog(version)
    return [VoiceDescriptor(**item) for item in raw if isinstance(item, dict)]


class SetVoiceRequest(BaseModel):
    voice_id: str


@app.patch("/session/{session_id}/voice")
async def update_session_voice(session_id: str, request: SetVoiceRequest):
    """Update the session's selected voice. Validates against the catalog."""
    session = _get_session(session_id)
    voice_id = (request.voice_id or "").strip()
    if not voice_id:
        raise HTTPException(status_code=400, detail="voice_id is required")

    # Validate against current catalog; invalidate cache on file changes
    _catalog_path = os.path.join(os.path.dirname(__file__), "voice_catalog.json")
    try:
        _version = os.path.getmtime(_catalog_path)
    except Exception:
        _version = 0.0
    catalog_ids = {item.get("id") for item in _load_voice_catalog(_version) if isinstance(item, dict)}
    if catalog_ids and voice_id not in catalog_ids:
        raise HTTPException(status_code=400, detail="Unknown voice_id")

    settings = session.get("voice_settings") or {}
    settings["voice_id"] = voice_id
    session["voice_settings"] = settings
    _persist_session_state(session_id, session)

    return {"ok": True, "voice_id": voice_id}


def _catalog_lookup() -> List[Dict[str, Any]]:
    """Helper to return the current voice catalog with cache invalidation."""
    path = os.path.join(os.path.dirname(__file__), "voice_catalog.json")
    try:
        version = os.path.getmtime(path)
    except Exception:
        version = 0.0
    return _load_voice_catalog(version)


@app.get("/voices/preview/{voice_id}")
async def voice_preview(voice_id: str):
    """Return an MP3 preview for the given voice.

    Strategy:
    - If a pre-generated preview file exists under app/static/voices, serve it.
    - Else, synthesize a short sample via OpenAI TTS and cache it to disk.
    """
    voice_id = (voice_id or "").strip().lower()
    if not voice_id:
        raise HTTPException(status_code=400, detail="voice_id is required")

    # Validate voice against catalog ids if available
    catalog = _catalog_lookup()
    valid_ids = {v.get("id") for v in catalog if isinstance(v, dict)}
    if valid_ids and voice_id not in valid_ids:
        raise HTTPException(status_code=404, detail="Unknown voice")

    # Serve cached/static file if present
    static_dir = os.path.join("app", "static", "voices")
    os.makedirs(static_dir, exist_ok=True)
    filename = f"{voice_id}-preview.mp3"
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")

    # If no API key, we can't synthesize a preview
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Preview unavailable")

    # Build a short sample utterance
    label = None
    for item in catalog:
        try:
            if item.get("id") == voice_id:
                label = item.get("label") or voice_id
                break
        except Exception:
            continue
    label = label or voice_id
    sample_text = f"Hello! This is the {label} voice sample for your interview practice."

    # Synthesize via OpenAI TTS HTTP API to avoid adding SDK complexity here
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            tts_resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini-tts",
                    "voice": voice_id,
                    "input": sample_text,
                    "format": "mp3",
                },
            )
            tts_resp.raise_for_status()
            audio_bytes = tts_resp.content
    except httpx.HTTPStatusError as exc:
        logger.exception("Voice preview synthesis failed: %s %s", exc.response.status_code, exc.response.text)
        raise HTTPException(status_code=exc.response.status_code, detail="Unable to synthesize preview")
    except Exception:
        logger.exception("Error generating voice preview")
        raise HTTPException(status_code=502, detail="Preview service error")

    # Cache to disk for subsequent requests
    try:
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
    except Exception:
        logger.exception("Failed to cache synthesized preview for %s", voice_id)

    return Response(content=audio_bytes, media_type="audio/mpeg")


# Helper functions
async def start_agent(session_id: str):
    """Start the interview agent for a session."""
    session = active_sessions.get(session_id)
    if session is None:
        stored = load_persisted_session(session_id)
        if stored is None:
            logger.warning("Session %s not found while starting agent", session_id)
            return
        session = stored
        active_sessions[session_id] = session

    if session.get("agent") is not None:
        logger.debug("Agent already active for session %s", session_id)
        return

    try:
        # Initialize the agent with session data
        agent = InterviewPracticeAgent(
            openai_api_key=OPENAI_API_KEY,
            openai_model=OPENAI_MODEL,
            resume_text=session["resume_text"],
            job_description_text=session["job_desc_text"],
            session_id=session_id,
        )

        # Start the agent
        await agent.start()

        # Store the agent in the session
        session["agent"] = agent
        _persist_session_state(session_id, session)

        logger.info("Agent started for session %s", session_id)
    except Exception:
        logger.exception("Error starting agent for session %s", session_id)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception for %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
