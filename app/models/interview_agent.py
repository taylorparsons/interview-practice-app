import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def get_base_coach_prompt() -> str:
    """Backwards compatibility alias for ruthless persona."""
    return get_coach_prompt("ruthless")


def get_coach_prompt(persona: str) -> str:
    persona = (persona or "ruthless").strip().lower()
    if persona == "helpful":
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
    if persona == "discovery":
        return (
            """
# Role:
You are a Discovery Interview Coach focused on eliciting strong narratives from the candidate's work history.

# Instructions:
- Help the candidate uncover and shape stories for common behavioral prompts (leadership, conflict, ambiguity, delivery, failure, customer focus).
- Use STAR + I and ask targeted questions to identify Situation, Task, Action, Result, and measurable Impact.
- Probe for specifics: scale, metrics, stakeholders, dates, risks, decisions, alternatives, trade-offs.
- Suggest how to phrase concise narrative bullets and how to adapt stories to different competencies.

# Style and Tone:
- Curious, supportive, and practical.
- Keep prompts short and focused.
- Provide concrete templates and example bullets when helpful.
            """
        ).strip()
    # default 'ruthless'
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

class InterviewPracticeAgent:
    def __init__(
        self,
        openai_api_key: str,
        openai_model: str,
        resume_text: str,
        job_description_text: str,
        session_id: Optional[str] = None,
        persona: str = "ruthless",
    ):
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.openai_model = openai_model
        self.session_id = session_id
        
        # Store document texts
        self.resume_text = resume_text
        self.job_description_text = job_description_text
        
        # Store interview state
        self.current_question_index = 0
        self.interview_questions = []
        self.user_answers = []
        self.feedback_history = []
        self.interview_in_progress = False
        
        log_prefix = f"session={session_id} " if session_id else ""
        self.persona = (persona or "ruthless").lower()
        logger.info("%sInitialized Interview Agent with OpenAI model: %s", log_prefix, openai_model)
    
    async def generate_interview_questions(self, num_questions: int = 5) -> List[str]:
        """Generate interview questions based on resume and job description."""
        system_prompt = get_coach_prompt(self.persona)
        
        user_prompt = f"""
        Resume:
        {self.resume_text}
        
        Job Description:
        {self.job_description_text}
        
        Generate {num_questions} interview questions for this candidate based on their resume and the job description.
        Return the response as a JSON array of question strings.
        """
        
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
        system_prompt = f"""
{get_coach_prompt(self.persona)}

Evaluate the candidate's answer to the interview question. Return a strict JSON object with keys:
- score (1-10), strengths [..], weaknesses [..], feedback (actionable), why_asked (competency), example_improvement (concise improved answer).
        """
        
        vt = (voice_transcript or "").strip()
        vt_block = f"\n\nVoice Transcript (if any):\n{vt}\n" if vt else ""

        user_prompt = f"""
        Interview Question: {question}
        
        Candidate's Answer: {answer}
        {vt_block}
        
        Please evaluate this response.
        """
        
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
        system_prompt = f"""
{base_prompt}

You are now providing a tailored, exemplary answer to the candidate's interview question.

Requirements:
- Draw directly from the candidate's resume wherever relevant (roles, companies, projects, technologies, metrics, scope, team size, timelines).
- Align to the job description priorities and mirror key terminology for the role.
- When applicable, structure with STAR + I (Situation, Task, Action, Result, Impact) and quantify outcomes with concrete numbers.
- Keep tone confident, concise, and conversational (not scripted).
- Target length ~120–220 words unless the question demands more.

Output:
- Return only the answer text, no preface, labels, or lists unless the question explicitly asks for them.
        """
        
        user_prompt = f"""
        Interview Question: {question}
        
        Please provide an exemplary answer to this question based on the following resume and job description:
        
        Resume:
        {self.resume_text}
        
        Job Description:
        {self.job_description_text}
        """
        
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
