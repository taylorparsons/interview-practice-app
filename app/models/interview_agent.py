import asyncio
import json
import os
import re
from typing import Dict, List, Any, Optional

import openai
from openai import AsyncOpenAI

class InterviewPracticeAgent:
    def __init__(
        self,
        livekit_url: str,
        api_key: str,
        api_secret: str,
        openai_api_key: str,
        openai_model: str,
        resume_text: str,
        job_description_text: str,
    ):
        # Store LiveKit connection info
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.openai_model = openai_model
        
        # Store document texts
        self.resume_text = resume_text
        self.job_description_text = job_description_text
        
        # Store interview state
        self.current_question_index = 0
        self.interview_questions = []
        self.user_answers = []
        self.feedback_history = []
        self.interview_in_progress = False
        
        print(f"Initialized Interview Agent with OpenAI model: {openai_model}")
    
    async def generate_interview_questions(self, num_questions: int = 5) -> List[str]:
        """Generate interview questions based on resume and job description."""
        system_prompt = """
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
        print(f"Raw API response: {content}")
        
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
            except Exception as e:
                # Fallback if all parsing attempts fail
                print(f"Error parsing questions: {e}")
                questions = [content]
        
        print(f"Parsed questions: {questions}")
        self.interview_questions = questions
        return questions
    
    async def evaluate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """Evaluate candidate's answer to an interview question."""
        system_prompt = """
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
- **Start with a warm, human touch:** Open with a tone that feels real and engaging—straightforward but grounded in a commitment to great service.
- **Keep it clear, keep it direct:** No jargon, no fluff. The language should be easy to follow, striking a balance between conversational and professional.
- **Make it approachable:** The summary should feel welcoming and relatable, reflecting the kind of service experience the company is known for.
- **Make it personal:** Tailor the message to the people in the room—acknowledge their perspectives, show you’re listening, and make it relevant.
- **Lead with confidence, not control:** Frame the information in a way that helps people make decisions and take action without feeling boxed in.
- **Give people what they need to move forward:** Keep it actionable, so attendees walk away informed and ready to take the next steps.
- **Respect every voice in the room:** Reflect the company’s commitment to diversity and inclusion—everyone’s input matters.
- **Stay curious, stay adaptable:** Encourage a mindset of testing, learning, and adjusting based on what works in the real world.
- **Avoid the use of these words:** Innovatively, Creatively, Effectively, Efficiently, Excellently, Exceptionally, Robustly, Seamlessly, Smartly, Successfully, Uniquely, Usefully, Beautifully, Compellingly, Comprehensively, Convincingly, Critically, Definitively, Distinctly, Diversely, Effortlessly, Elegantly, Intelligently, Meticulously, Potentially, Primarily, Productively, Professionally, Remarkably

Provide your evaluation in JSON format with the following structure:
{
 "score": <score from 1-10>,
 "strengths": ["strength1", "strength2", ...],
 "weaknesses": ["weakness1", "weakness2", ...],
 "feedback": "detailed feedback with improvement suggestions",
 "example_improvement": "example of an improved answer"
}
        """
        
        user_prompt = f"""
        Interview Question: {question}
        
        Candidate's Answer: {answer}
        
        Please evaluate this response.
        """
        
        print(f"Evaluating answer for question: {question}")
        
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
        print(f"Raw evaluation response: {content}")
        
        try:
            # Try to directly parse the JSON
            evaluation = json.loads(content)
            print(f"Successfully parsed evaluation JSON: {evaluation}")
            
            # Ensure all required fields are present
            required_fields = ["score", "strengths", "weaknesses", "feedback", "example_improvement"]
            missing_fields = [field for field in required_fields if field not in evaluation]
            
            if missing_fields:
                print(f"Warning: Missing fields in evaluation response: {missing_fields}")
                # Add default values for missing fields
                for field in missing_fields:
                    if field == "score":
                        evaluation[field] = 5
                    elif field in ["strengths", "weaknesses"]:
                        evaluation[field] = [f"No {field} provided"]
                    else:
                        evaluation[field] = f"No {field.replace('_', ' ')} provided"
                
        except json.JSONDecodeError as e:
            print(f"Error parsing evaluation JSON: {e}")
            
            # Try to extract JSON from the text
            try:
                # Look for JSON-like structure in the response
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    print(f"Extracted JSON string: {json_str}")
                    evaluation = json.loads(json_str)
                    print(f"Successfully parsed extracted JSON: {evaluation}")
                else:
                    raise ValueError("No JSON structure found in response")
            except Exception as e2:
                print(f"Error extracting JSON: {e2}")
                # Fallback to text response
                evaluation = {
                    "score": 5,
                    "strengths": ["Unable to parse structured feedback"],
                    "weaknesses": ["Unable to parse structured feedback"],
                    "feedback": content,
                    "example_improvement": "N/A"
                }
                print(f"Using fallback evaluation: {evaluation}")
        
        # Store feedback in history
        self.feedback_history.append(evaluation)
        
        return evaluation
    
    async def generate_example_answer(self, question: str) -> str:
        """Generate an example good answer to an interview question."""
        system_prompt = """
        You are an expert interview coach helping candidates prepare for job interviews.
        Provide an exemplary answer to the given interview question.
        The answer should be:
        1. Clear, concise, and well-structured
        2. Include specific examples where appropriate
        3. Demonstrate relevant skills and experiences
        4. Address the underlying competency being tested
        5. Sound natural and conversational, not rehearsed
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
        """Start the interview agent."""
        print("Starting Interview Practice Agent")
        await self.connect()
        
    async def connect(self) -> None:
        """Connect to LiveKit (simplified implementation)."""
        print(f"Connected to LiveKit at {self.livekit_url}")
        # In a real implementation, we would connect to the LiveKit server here
        # For now, we'll just simulate a successful connection

    async def send_message(self, participant, message):
        """Send a message to a participant (simplified implementation)."""
        print(f"[AGENT] Sending message to participant: {message}")
        
    async def send_audio(self, participant, text):
        """Send audio to a participant (simplified implementation)."""
        print(f"[AGENT] Converting to audio and sending: {text}")
    
    async def process_interview_question(self, participant, question_index):
        """Process an interview question (simplified implementation)."""
        print(f"[AGENT] Processing interview question {question_index}")
    
    async def process_answer_evaluation(self, participant, question, answer):
        """Process answer evaluation (simplified implementation)."""
        print(f"[AGENT] Evaluating answer for question: {question}")
        
    async def process_interview_summary(self, participant):
        """Process interview summary (simplified implementation)."""
        print(f"[AGENT] Generating interview summary")