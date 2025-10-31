import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from openai import AsyncOpenAI
from app.utils.prompt_loader import load_prompt_template

logger = logging.getLogger(__name__)


def get_base_coach_prompt() -> str:
    """Return the legacy default coach prompt (ruthless).

    This exists for backward compatibility with older code paths that
    expect a single, non‑persona system prompt.
    """
    return get_coach_prompt("ruthless")

def _prompt_helpful() -> str:
    """System prompt content for the Helpful coach persona."""
    return (
        """
# Role:
You are a Helpful Interview Coach. Your goal is to guide the candidate with constructive, empathetic, and clear feedback so they can iteratively improve their answers.

# Instructions:
- Encourage, coach, and suggest improvements without being harsh.
- Use STAR + I (Situation, Task, Action, Result, Impact) to frame feedback.
- Ask gentle follow-up questions to fill gaps (e.g., metrics, scope, constraints, timeline, team, trade-offs).
- Pull in relevant resume/job description context to tailor guidance.

# Style and Tone:
- Positive, collaborative, and specific.
- Use plain, direct language.
- Focus on actionable tips and example phrasing.
        """
    ).strip()


def _prompt_discovery() -> str:
    """System prompt content for the Discovery coach persona."""
    return (
        """
# Project Instructions: Voice Agent for Work History Narrative Discovery (RISEN++)

## Role:
You are a Discovery Interview Coach helping users explore meaningful stories from their work history. Your job is to guide reflection, not to rehearse answers.

## Instructions:
Lead users through short, thoughtful conversations to help them uncover real experiences that show leadership, conflict resolution, ambiguity, ownership, failure, and customer impact. Use the STAR + Impact model as a gentle framework, not a script.

Ask open-ended questions, listen actively, and help users shape their stories naturally. Keep the tone curious and supportive.

## Steps:
1. Start broad: Ask reflective prompts like:
   - “What’s a time you were most proud of your work?”
   - “When did you face a tough decision at work?”
2. Let them share freely. Listen for a clear Situation and Task.
3. Guide them to unpack Actions and Results with simple follow-ups like:
   - “What did you do next?”
   - “What changed because of your actions?”
4. Ask about Impact: “What was the outcome? Did it affect people, goals, or customers?”
5. Gently probe: scope, stakeholders, decisions, trade-offs.
6. Reflect back what you hear: “Sounds like a leadership moment. Want to explore that angle?”
7. Help them summarize with phrases like: “So that shows your ability to lead under pressure.”

## Expectations:
- Keep the user talking and reflecting, not just answering.
- Surface rich, specific work stories tied to real challenges and outcomes.
- Highlight transferable themes like ownership or learning.
- Keep each turn short and easy to process.
- Offer to explore the same story from different angles if it fits multiple themes.

## Narrow:
- Focus only on professional or academic experiences.
- No resume writing, technical prep, or mock interviews.
- Always keep it discovery-focused, not performance-based.

## Rating:
Internally rate each interaction on:
- Depth of story discovery
- Clarity of STAR elements
- Engagement and reflection by the user
- Tone and pace

If below 0.8, simplify your questions and slow down the pace for better user clarity.

## Style and Tone:
- Warm, curious, and encouraging.
- Use short sentences and natural phrasing.
- Let silence be okay—give users space to think.
- Avoid jargon; speak like a thoughtful guide, not an evaluator.
        """
    ).strip()


def _prompt_ruthless() -> str:
    """System prompt content for the Ruthless coach persona."""
    return (
        """
# Role:
You are a Ruthless Interview Preparation Coach. Your expertise lies in identifying and correcting any mistakes in communication, ensuring the user is always on point and ready to excel in high-pressure interview scenarios.

# Instructions:
- Challenge the candidate; be direct and precise.
- Start from the customer perspective.
- Enforce STAR + I structure and request quantification.
- Maintain high standards; point out flaws quickly and suggest corrections.

# Style and Tone:
- Relentless, clear, and exacting.
- Keep answers concise and defensible under scrutiny.
        """
    ).strip()


def get_coach_prompt(persona: str) -> str:
    """Return the system prompt for a given coach persona.

    - Normalizes the provided ``persona`` slug (ruthless | helpful | discovery).
    - Falls back to the ruthless prompt if the slug is missing or unknown.
    """
    slug = (persona or "ruthless").strip().lower()
    if slug == "helpful":
        return _prompt_helpful()
    if slug == "discovery":
        return _prompt_discovery()
    return _prompt_ruthless()

@dataclass
class InterviewAgentConfig:
    """Configuration for InterviewPracticeAgent.

    Encapsulates required model credentials, session metadata, and persona
    so the agent constructor avoids a long parameter list.
    """
    openai_api_key: str
    openai_model: str
    resume_text: str
    job_description_text: str
    session_id: Optional[str] = None
    persona: str = "ruthless"


class InterviewPracticeAgent:
    """Asynchronous interview coach for generating questions and feedback.

    Uses OpenAI's Chat Completions API to:
    - Generate interview questions from resume + job description
    - Evaluate candidate answers into structured feedback
    - Produce exemplar answers tailored to the candidate
    """

    def __init__(self, config: InterviewAgentConfig):
        """Initialize the agent from a configuration object.

        Parameters
        - config: InterviewAgentConfig with API credentials, resume/JD text,
          session id, and selected persona.
        """
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.openai_model = config.openai_model
        self.session_id = config.session_id

        # Store document texts
        self.resume_text = config.resume_text
        self.job_description_text = config.job_description_text

        # Store interview state
        self.current_question_index = 0
        self.interview_questions = []
        self.user_answers = []
        self.feedback_history = []
        self.interview_in_progress = False

        log_prefix = f"session={config.session_id} " if config.session_id else ""
        self.persona = (config.persona or "ruthless").lower()
        logger.info("%sInitialized Interview Agent with OpenAI model: %s", log_prefix, config.openai_model)
    
    async def generate_interview_questions(self, num_questions: int = 5) -> List[str]:
        """Generate interview questions based on resume and job description."""
        system_prompt = load_prompt_template(self.persona, "questions", "system") or get_coach_prompt(self.persona)

        user_tpl = load_prompt_template(self.persona, "questions", "user") or (
            "Resume:\n{resume_text}\n\nJob Description:\n{job_description_text}\n\n"
            "Generate {num_questions} interview questions for this candidate based on their resume and the job description.\n"
            "Return the response as a JSON array of question strings."
        )
        user_prompt = user_tpl.format(
            resume_text=self.resume_text,
            job_description_text=self.job_description_text,
            num_questions=num_questions,
        )
        
        # Generate questions using the ChatGPT API
        response = await self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )
        
        content = response.choices[0].message.content
        logger.debug("Raw interview question response: %s", content)
        
        # Extract and parse the questions
        try:
            # Try to directly parse the response as JSON
            questions_data = json.loads(content)
            
            # Handle both array of strings and array of objects
            questions = []
            for item in questions_data:
                if isinstance(item, str):
                    questions.append(item)
                elif isinstance(item, dict) and "question" in item:
                    questions.append(item["question"])
                else:
                    # If we can't parse it properly, just use the string representation
                    questions.append(str(item))
                    
        except json.JSONDecodeError:
            # If direct parsing fails, extract the JSON part
            try:
                # Look for JSON array in the response
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    questions_json = content[start_idx:end_idx]
                    questions_data = json.loads(questions_json)
                    
                    # Handle both array of strings and array of objects
                    questions = []
                    for item in questions_data:
                        if isinstance(item, str):
                            questions.append(item)
                        elif isinstance(item, dict) and "question" in item:
                            questions.append(item["question"])
                        else:
                            # If we can't parse it properly, just use the string representation
                            questions.append(str(item))
                else:
                    # If no JSON array is found, split by newlines and clean up
                    questions = [q.strip() for q in content.split('\n') if q.strip()]
            except Exception:
                # Fallback if all parsing attempts fail
                logger.exception("Error parsing questions from model response")
                questions = [content]
        
        logger.debug("Parsed interview questions: %s", questions)
        self.interview_questions = questions
        return questions
    
    async def evaluate_answer(self, question: str, answer: str, voice_transcript: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate candidate's answer to an interview question."""
        system_prompt = load_prompt_template(self.persona, "evaluation", "system") or (
            f"{get_coach_prompt(self.persona)}\n\n"
            "Evaluate the candidate's answer to the interview question. Return a strict JSON object with keys:\n"
            "- score (1-10), strengths [..], weaknesses [..], feedback (actionable), why_asked (competency), example_improvement (concise improved answer)."
        )
        
        vt = (voice_transcript or "").strip()
        user_tpl = load_prompt_template(self.persona, "evaluation", "user") or (
            "Interview Question: {question}\n\n"
            "Candidate's Answer: {answer}\n\n"
            "{voice_transcript_block}\n"
            "Please evaluate this response."
        )
        vt_block = f"Voice Transcript (if any):\n{vt}\n\n" if vt else ""
        user_prompt = user_tpl.format(question=question, answer=answer, voice_transcript_block=vt_block)
        
        logger.info("Evaluating answer for question: %s", question)
        
        # Generate evaluation using ChatGPT API
        response = await self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )
        
        # Extract and parse the evaluation
        content = response.choices[0].message.content
        logger.debug("Raw evaluation response: %s", content)
        
        try:
            # Try to directly parse the JSON
            evaluation = json.loads(content)
            logger.debug("Successfully parsed evaluation JSON: %s", evaluation)
            
            # Ensure all required fields are present
            required_fields = ["score", "strengths", "weaknesses", "feedback", "example_improvement", "why_asked"]
            missing_fields = [field for field in required_fields if field not in evaluation]
            
            if missing_fields:
                logger.warning("Missing fields in evaluation response: %s", missing_fields)
                # Add default values for missing fields
                for field in missing_fields:
                    if field == "score":
                        evaluation[field] = 5
                    elif field in ["strengths", "weaknesses"]:
                        evaluation[field] = [f"No {field} provided"]
                    else:
                        evaluation[field] = f"No {field.replace('_', ' ')} provided"
                
        except json.JSONDecodeError as e:
            logger.exception("Error parsing evaluation JSON")
            
            # Try to extract JSON from the text
            try:
                # Look for JSON-like structure in the response
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    logger.debug("Extracted JSON string: %s", json_str)
                    evaluation = json.loads(json_str)
                    logger.debug("Successfully parsed extracted JSON: %s", evaluation)
                else:
                    raise ValueError("No JSON structure found in response")
            except Exception as e2:
                logger.exception("Error extracting JSON when parsing evaluation response")
                # Fallback to text response
                evaluation = {
                    "score": 5,
                    "strengths": ["Unable to parse structured feedback"],
                    "weaknesses": ["Unable to parse structured feedback"],
                    "feedback": content,
                    "example_improvement": "N/A"
                }
                logger.info("Using fallback evaluation: %s", evaluation)
        
        # Store feedback in history
        self.feedback_history.append(evaluation)
        
        return evaluation
    
    async def generate_example_answer(self, question: str) -> str:
        """Generate an example good answer to an interview question."""
        base_prompt = get_coach_prompt(self.persona)
        system_prompt = load_prompt_template(self.persona, "example", "system") or (
            f"{base_prompt}\n\n"
            "You are now providing a tailored, exemplary answer to the candidate's interview question.\n\n"
            "Requirements:\n"
            "- Draw directly from the candidate's resume wherever relevant (roles, companies, projects, technologies, metrics, scope, team size, timelines).\n"
            "- Align to the job description priorities and mirror key terminology for the role.\n"
            "- When applicable, structure with STAR + I (Situation, Task, Action, Result, Impact) and quantify outcomes with concrete numbers.\n"
            "- Keep tone confident, concise, and conversational (not scripted).\n"
            "- Target length ~120–220 words unless the question demands more.\n\n"
            "Output:\n- Return only the answer text, no preface, labels, or lists unless the question explicitly asks for them."
        )

        user_tpl = load_prompt_template(self.persona, "example", "user") or (
            "Interview Question: {question}\n\n"
            "Please provide an exemplary answer to this question based on the following resume and job description:\n\n"
            "Resume:\n{resume_text}\n\nJob Description:\n{job_description_text}"
        )
        user_prompt = user_tpl.format(
            question=question,
            resume_text=self.resume_text,
            job_description_text=self.job_description_text,
        )
        
        # Generate example answer using the ChatGPT API
        response = await self.client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )
        
        return response.choices[0].message.content
    
    async def start(self) -> None:
        """Initialize the interview agent (placeholder for backward compatibility)."""
        logger.info("Interview Practice Agent ready with OpenAI backend only")

    async def send_message(self, participant, message):
        """Send a message to a participant (simplified implementation)."""
        logger.debug("[AGENT] Sending message to participant: %s", message)
        
    async def send_audio(self, participant, text):
        """Send audio to a participant (simplified implementation)."""
        logger.debug("[AGENT] Converting to audio and sending: %s", text)
    
    async def process_interview_question(self, participant, question_index):
        """Process an interview question (simplified implementation)."""
        logger.debug("[AGENT] Processing interview question %s", question_index)
    
    async def process_answer_evaluation(self, participant, question, answer):
        """Process answer evaluation (simplified implementation)."""
        logger.debug("[AGENT] Evaluating answer for question: %s", question)
        
    async def process_interview_summary(self, participant):
        """Process interview summary (simplified implementation)."""
        logger.debug("[AGENT] Generating interview summary")
