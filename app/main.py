import logging
import os
import asyncio
import textwrap
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
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
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS
)
from app.utils.document_processor import allowed_file, save_uploaded_file, save_text_as_file, process_documents
from app.models.interview_agent import InterviewPracticeAgent
from app.logging_config import setup_logging
from app.utils.session_store import (
    save_session as persist_session,
    load_session as load_persisted_session,
    delete_session as delete_persisted_session,
)

setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Interview Practice App")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Store active interview sessions
active_sessions = {}


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


# Request and response models
class DocumentUploadResponse(BaseModel):
    session_id: str
    message: str


class GenerateQuestionsRequest(BaseModel):
    session_id: str
    num_questions: int = 5


class GenerateQuestionsResponse(BaseModel):
    questions: List[str]


class EvaluateAnswerRequest(BaseModel):
    session_id: str
    question: str
    answer: str


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
    session_data = {
        "resume_path": resume_path,
        "job_desc_path": job_desc_path,
        "resume_text": resume_text,
        "job_desc_text": job_desc_text,
        "questions": [],
        "answers": [],
        "evaluations": [],
        "agent": None,
        "current_question_index": 0,
    }

    _persist_session_state(session_id, session_data)
    
    # Initialize and start the agent in the background
    if background_tasks:
        background_tasks.add_task(start_agent, session_id)
    
    return {"session_id": session_id, "message": "Documents uploaded successfully"}


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

    if session.get("agent") is not None:
        try:
            agent = session["agent"]
            evaluation = await agent.evaluate_answer(request.question, request.answer)

            if "answers" not in session:
                session["answers"] = []
            if "evaluations" not in session:
                session["evaluations"] = []

            session["answers"].append({"question": request.question, "answer": request.answer})
            session["evaluations"].append(evaluation)
            session["current_question_index"] = len(session["answers"])
            _persist_session_state(session_id, session)

            return {"evaluation": evaluation}
        except Exception:
            logger.exception("Error using agent to evaluate answer for session %s", session_id)
    
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
        "content": {
            "relevance": min(10, 5 + len(set(request.question.lower().split()).intersection(set(request.answer.lower().split())))),
            "depth": 5 if answer_length > 200 else 3
        },
        "tone": {
            "clarity": 7,
            "professionalism": 8
        }
    }
    
    if "answers" not in session:
        session["answers"] = []
    if "evaluations" not in session:
        session["evaluations"] = []
    
    session["answers"].append({"question": request.question, "answer": request.answer})
    session["evaluations"].append(evaluation)
    session["current_question_index"] = len(session["answers"])
    _persist_session_state(session_id, session)

    return {"evaluation": evaluation}


@app.post("/generate-example-answer", response_model=ExampleAnswerResponse)
async def generate_example_answer(request: ExampleAnswerRequest):
    session_id = request.session_id
    session = _get_session(session_id)

    if session.get("agent") is not None:
        try:
            agent = session["agent"]
            example_answer = await agent.generate_example_answer(request.question)

            return {"answer": example_answer}
        except Exception:
            logger.exception("Error generating example answer for session %s", session_id)
    
    question = request.question.lower()
    
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
        "questions": session["questions"],
        "answers": session["answers"],
        "evaluations": session["evaluations"],
        "current_question_index": session.get("current_question_index", 0),
    }


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


def _truncate_text(text: str, limit: int = 1200) -> str:
    """Return a trimmed preview of longer text snippets."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _build_voice_instructions(session_id: str, session: Dict[str, Any]) -> str:
    """Create instructions for the realtime voice agent based on session context."""
    questions: List[str] = session.get("questions") or []
    first_question = questions[0] if questions else "Tell me about yourself."
    question_bullets = "\n".join(f"- {q}" for q in questions[:5]) or "- Ask situational and behavioral questions tailored to the role."
    resume_excerpt = _truncate_text(session.get("resume_text", ""), 1500)
    job_desc_excerpt = _truncate_text(session.get("job_desc_text", ""), 1500)

    instructions = f"""
You are a realtime voice interview coach for session {session_id}.

Candidate resume excerpt:
{resume_excerpt}

Job description excerpt:
{job_desc_excerpt}

Interview question plan:
{question_bullets}

Conduct a conversational mock interview. Start with a brief greeting, then ask the first question exactly as "{first_question}". 
Listen to the candidate's voice response. After they finish, provide concise, constructive feedback and practical tips (under 4 sentences). 
Proceed through the remaining questions naturally. If the candidate asks for clarification or coaching, offer targeted guidance.
Keep responses under 30 seconds and always send a short text summary alongside audio so the UI can display the feedback.
Wrap up when the candidate indicates they are done or when the planned questions are covered.
"""
    return textwrap.dedent(instructions).strip()


@app.post("/voice/session", response_model=VoiceSessionResponse)
async def create_voice_session(request: VoiceSessionRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key is not configured")

    session = _get_session(request.session_id)
    voice_name = request.voice or OPENAI_REALTIME_VOICE
    instructions = _build_voice_instructions(request.session_id, session)

    payload = {
        "model": OPENAI_REALTIME_MODEL,
        "modalities": ["audio", "text"],
        "voice": voice_name,
        "instructions": instructions,
    }

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
