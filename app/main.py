import os
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request
import uvicorn

# Import local modules
from app.config import (
    LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
    OPENAI_API_KEY, OPENAI_MODEL, UPLOAD_FOLDER, ALLOWED_EXTENSIONS
)
from app.utils.document_processor import allowed_file, save_uploaded_file, process_documents
from app.models.interview_agent import InterviewPracticeAgent

# Initialize FastAPI
app = FastAPI(title="Interview Practice App")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Store active interview sessions
active_sessions = {}


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


# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload-documents", response_model=DocumentUploadResponse)
async def upload_documents(
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    # Check if files are valid
    if not allowed_file(resume.filename) or not allowed_file(job_description.filename):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    # Create session ID
    session_id = str(uuid.uuid4())
    
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Save uploaded files
    resume_path = save_uploaded_file(resume, UPLOAD_FOLDER, session_id + "_resume")
    job_desc_path = save_uploaded_file(job_description, UPLOAD_FOLDER, session_id + "_job_description")
    
    # Process documents
    resume_text, job_desc_text = await process_documents(resume_path, job_desc_path)
    
    # Store session data
    active_sessions[session_id] = {
        "resume_path": resume_path,
        "job_desc_path": job_desc_path,
        "resume_text": resume_text,
        "job_desc_text": job_desc_text,
        "questions": [],
        "answers": [],
        "evaluations": [],
        "agent": None
    }
    
    # Initialize and start the agent in the background
    if background_tasks:
        background_tasks.add_task(start_agent, session_id)
    
    return {"session_id": session_id, "message": "Documents uploaded successfully"}


@app.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    session_id = request.session_id
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    if session.get("agent") is not None:
        try:
            agent = session["agent"]
            questions = await agent.generate_interview_questions(request.num_questions)
            
            session["questions"] = questions
            active_sessions[session_id] = session
            
            return {"questions": questions}
        except Exception as e:
            print(f"Error using agent to generate questions: {str(e)}")
            pass
    
    job_desc = session["job_desc_text"] if "job_desc_text" in session else ""
    
    default_questions = [
        "Tell me about your experience and background.",
        "What are your greatest professional strengths?",
        "What do you consider to be your weaknesses?",
        "Why are you interested in this position?",
        "Where do you see yourself in five years?"
    ]
    
    questions = default_questions
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
    active_sessions[session_id] = session
    
    return {"questions": questions[:request.num_questions]}


@app.post("/evaluate-answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer(request: EvaluateAnswerRequest):
    session_id = request.session_id
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
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
            active_sessions[session_id] = session
            
            return {"evaluation": evaluation}
        except Exception as e:
            print(f"Error using agent to evaluate answer: {str(e)}")
            pass
    
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
    active_sessions[session_id] = session
    
    return {"evaluation": evaluation}


@app.post("/generate-example-answer", response_model=ExampleAnswerResponse)
async def generate_example_answer(request: ExampleAnswerRequest):
    session_id = request.session_id
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    if session.get("agent") is not None:
        try:
            agent = session["agent"]
            example_answer = await agent.generate_example_answer(request.question)
            
            return {"answer": example_answer}
        except Exception as e:
            print(f"Error using agent to generate example answer: {str(e)}")
            pass
    
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
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    return {
        "session_id": session_id,
        "questions": session["questions"],
        "answers": session["answers"],
        "evaluations": session["evaluations"],
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    try:
        os.remove(session["resume_path"])
        os.remove(session["job_desc_path"])
    except Exception as e:
        print(f"Error cleaning up files: {str(e)}")
    
    del active_sessions[session_id]
    
    return {"message": "Session deleted successfully"}


# Helper functions
async def start_agent(session_id: str):
    """Start the interview agent for a session."""
    if session_id not in active_sessions:
        print(f"Session {session_id} not found")
        return
    
    session = active_sessions[session_id]
    
    try:
        # Initialize the agent with session data
        agent = InterviewPracticeAgent(
            livekit_url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
            openai_api_key=OPENAI_API_KEY,
            openai_model=OPENAI_MODEL,
            resume_text=session["resume_text"],
            job_description_text=session["job_desc_text"]
        )
        
        # Start the agent
        await agent.start()
        
        # Store the agent in the session
        session["agent"] = agent
        active_sessions[session_id] = session
        
        print(f"Agent started for session {session_id}")
    except Exception as e:
        print(f"Error starting agent for session {session_id}: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)