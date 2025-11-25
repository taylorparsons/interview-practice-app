import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

from openai import AsyncOpenAI
from app.models.prompts import build_dual_level_prompt

logger = logging.getLogger(__name__)


def get_base_coach_prompt() -> str:
    """Base system-level prompt used to define the interview coach persona.

    Shared by text features and can be reused by the realtime voice agent
    to ensure consistent behavior and tone.
    """
    return (
        """
        # Role:
You are a Ruthless Interview Preparation Coach. Your expertise lies in identifying and correcting any mistakes in communication, ensuring the user is always on point and ready to excel in high-pressure interview scenarios.

# Instructions:
Challenge the user to craft a system message that is flawless and precise, ensuring they effectively sell themselves. The message should be devoid of any errors, ambiguities, or unnecessary elements, reflecting the user's capability to lead and communicate effectively in an interview setting. Emphasize the importance of starting with the customer perspective and using the STAR + I (Situation, Task, Action, Result, Impact) format for behavioral questions. Have the user's resume and the company's job description on hand, and interview the user using the style the company is known for.

# Steps:
1. **Identify any mistakes immediately** – Point out errors in grammar, tone, or content without hesitation.
2. **Demand clarity and precision** – Ensure every word serves a purpose and contributes to the overall message.
3. **Challenge assumptions and logic** – Question the user's reasoning and ensure their message is logically sound.
4. **Push for excellence** – Encourage the user to refine their message until it is impeccable.
5. **Simulate high-pressure scenarios** – Prepare the user for real-world interview challenges by simulating tough questioning.
6. **Focus on customer-centric responses** – Guide the user to start answers with the customer perspective and work from the inside out.
7. **Utilize the STAR + I format** – Ensure the user structures behavioral responses to highlight the Situation, Task, Action, Result, and Impact.
8. **Provide examples if asked** – Offer examples of what is expected, but do not accept any excuses for errors or lack of preparation.
9. **Leverage available resources** – Use the user's resume and the company's job description to tailor the interview style to what the company is known for.

# Expectations:
- The message should be error-free and demonstrate leadership qualities.
- It should be concise, impactful, and leave no room for misinterpretation.
- The tone should be assertive and confident, reflecting the user's readiness for leadership roles.
- The message should withstand scrutiny and challenge.
- Responses should effectively sell the user's skills and experiences.

# Narrow:
- Focus on interview preparation rather than casual networking.
- Avoid any language that could be perceived as weak or uncertain.
- Keep the message adaptable for various interview contexts and roles.

# Rating:
"Evaluate the response on a scale from 0 to 1 based on precision, clarity, alignment with leadership qualities, and effectiveness in preparing the user for interviews. Consider whether the message is likely to impress and withstand critical evaluation."

# Style and Tone:
- **Be relentless and direct:** No room for error—every mistake is an opportunity for improvement.
- **Keep it sharp and focused:** The language should be precise and to the point.
- **Make it challenging:** Push the user to think critically and refine their message.
- **Make it authoritative:** The message should convey confidence and command respect.
- **Lead with high standards:** Set the bar high and ensure the user meets it.
- **Give people the tools to excel:** Equip the user with the skills needed to succeed in interviews.
- **Respect the user's potential:** Acknowledge their capability to rise to the challenge.
- **Stay rigorous and demanding:** Encourage a mindset of continuous improvement and excellence.
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
        logger.info("%sInitialized Interview Agent with OpenAI model: %s", log_prefix, openai_model)
    
    async def generate_interview_questions(self, num_questions: int = 5) -> List[str]:
        """Generate interview questions based on resume and job description."""
        system_prompt = get_base_coach_prompt()
        
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
    
    async def evaluate_answer(self, question: str, answer: str, voice_transcript: Optional[str] = None, *, level: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate candidate's answer to an interview question."""
        # Respect the session-selected coach persona; default to level_1 (Help)
        # when the caller does not provide an explicit level.
        level = level or "level_1"
        system_prompt = build_dual_level_prompt(level)
        
        vt = (voice_transcript or "").strip()
        vt_block = f"\n\nVoice Transcript (if any):\n{vt}\n" if vt else ""

        user_prompt = f"""
        Interview Question: {question}
        
        Candidate's Answer: {answer}
        {vt_block}
        
        Please evaluate this response.
        """
        
        logger.info("Evaluating answer for question: %s (level=%s)", question, level)
        
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
        content = response.choices[0].message.content or ""
        logger.debug("Raw evaluation response: %s", content)

        # Guard: empty or non-JSON content should not raise noisy exceptions
        text = content.strip()
        if not text:
            logger.warning("Empty evaluation response from model; using fallback")
            evaluation = {
                "score": 5,
                "strengths": ["No structured feedback provided"],
                "weaknesses": ["No structured feedback provided"],
                "feedback": "",
                "example_improvement": "N/A",
                "why_asked": ""
            }
        else:
            try:
                # Fast path: only try direct JSON when it looks like JSON
                if text.startswith("{") or text.startswith("["):
                    evaluation = json.loads(text)
                else:
                    raise json.JSONDecodeError("Not JSON start", text, 0)

                logger.debug("Successfully parsed evaluation JSON: %s", evaluation)

                # Ensure all required fields are present
                required_fields = ["score", "strengths", "weaknesses", "feedback", "example_improvement", "why_asked"]
                missing_fields = [field for field in required_fields if field not in evaluation]

                if missing_fields:
                    logger.warning("Missing fields in evaluation response: %s", missing_fields)
                    for field in missing_fields:
                        if field == "score":
                            evaluation[field] = 5
                        elif field in ["strengths", "weaknesses"]:
                            evaluation[field] = [f"No {field} provided"]
                        else:
                            evaluation[field] = f"No {field.replace('_', ' ')} provided"

            except json.JSONDecodeError:
                # Try to extract JSON from the text (best‑effort) without noisy stack traces
                logger.warning("Evaluation response not valid JSON; attempting extraction")
                try:
                    match = re.search(r"\{.*\}", text, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        evaluation = json.loads(json_str)
                        logger.debug("Parsed JSON after extraction: %s", evaluation)
                    else:
                        raise ValueError("No JSON object found")
                except Exception:
                    # Fallback to text response with best-effort bullet extraction
                    bullets = self._extract_bullets(text)
                    strengths = bullets[:2] or ["Review the content feedback for key strengths."]
                    weaknesses = bullets[2:5] or bullets or ["Focus on clarifying structure and impact using STAR + I."]
                    example_improvement = " ".join(weaknesses[:2]).strip() or "Tighten STAR + I structure and quantify impact."
                    evaluation = {
                        "score": 5,
                        "strengths": strengths,
                        "weaknesses": weaknesses,
                        "feedback": text,
                        "example_improvement": example_improvement,
                        "why_asked": ""
                    }
                    logger.info("Using fallback evaluation (text only, parsed heuristically)")
        
        # Store feedback in history
        self.feedback_history.append(evaluation)
        
        return evaluation

    def _extract_bullets(self, text: str) -> List[str]:
        """Best-effort extraction of bullet/sentence fragments from free-form feedback."""
        bullets: List[str] = []
        for line in text.splitlines():
            l = line.strip()
            if not l:
                continue
            bullet_match = re.match(r"^[-*•]\s*(.+)$", l)
            numbered_match = re.match(r"^\d+[.)]\s*(.+)$", l)
            if bullet_match:
                bullets.append(bullet_match.group(1).strip())
            elif numbered_match:
                bullets.append(numbered_match.group(1).strip())
        if not bullets:
            # Fall back to sentence chunks
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for s in sentences:
                s = (s or "").strip()
                if len(s) > 20:
                    bullets.append(s)
                if len(bullets) >= 6:
                    break
        return bullets
    
    async def generate_example_answer(self, question: str) -> str:
        """Generate an example good answer to an interview question."""
        base_prompt = get_base_coach_prompt()
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
