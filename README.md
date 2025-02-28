# Interview Practice App

## Overview
An AI-powered interview practice application that helps job seekers prepare for interviews by generating personalized questions, providing real-time feedback, and offering example answers.

## Features
- Resume and Job Description Upload
- AI-Generated Interview Questions
- Real-Time Answer Evaluation
- Markdown-Formatted Example Answers
- Tone and Content Feedback Analysis

## Prerequisites
- Python 3.9+
- pip
- Virtual Environment

## Setup Instructions
1. Clone the repository
```bash
git clone https://github.com/yourusername/interview-practice-app.git
cd interview-practice-app
```

2. Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Dependencies
```bash
pip install -r requirements.txt
```

4. Set Up Environment Variables
Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

5. Run the Application
```bash
python app.py
```

## Technologies Used
- Flask
- OpenAI GPT
- Tailwind CSS
- Showdown.js
- Python Machine Learning Libraries

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Contact
Taylor Parsons - taylor.parsons@example.com

Project Link: [https://github.com/yourusername/interview-practice-app](https://github.com/yourusername/interview-practice-app)

---

## Lean Canvas

| Problem | Solution | Unique Value Proposition | Unfair Advantage | Customer Segments |
|---------|----------|--------------------------|------------------|-------------------|
| - Job seekers struggle with interview preparation<br>- Lack of personalized practice<br>- Difficulty receiving constructive feedback | - Question generation from job descriptions and resumes<br>- Real-time feedback on answers<br>- Resume-based example answers | - Personalized interview questions and feedback<br>- Real-time interaction using AI analysis<br>- Comprehensive practice tool | - Advanced AI models for evaluation<br>- Personalized adaptive feedback | - Job seekers<br>- Career coaches<br>- Educational institutions |

| Channels | Revenue Streams | Cost Structure | Key Metrics |
|----------|----------------|----------------|-------------|
| - Online platforms<br>- Career service partnerships<br>- Digital marketing | - Subscription model<br>- One-time purchases<br>- Institutional partnerships | - Development and maintenance<br>- AI model licensing<br>- Marketing costs | - Active users<br>- Engagement metrics<br>- Conversion rates |

---

## Technical Requirements Document

### 1. File Upload Capability
- **User Given**: As a user, I want to upload a job description and my resume easily.
- **When**: The user uploads these documents, they should be stored securely for processing.
- **Outcome**: Documents are used to tailor the interview questions specifically to the job description and user's experience.

### 2. Question Generation
- **User Given**: As a user, I want relevant interview questions generated from my resume and the job description.
- **When**: The user uploads documents, the system should analyze them instantly.
- **Outcome**: A set of personalized interview questions is generated and presented to the user.

### 3. User Answer Interaction
- **User Given**: As a user, I want to answer interview questions interactively.
- **When**: The system presents a question, the user should be able to respond easily.
- **Outcome**: The system records user answers for evaluation.

### 4. Answer Evaluation
- **User Given**: As a user, I want my answers evaluated for content and tone.
- **When**: The user submits an answer, it should be analyzed immediately.
- **Outcome**: The system provides feedback on the content accuracy and tone of the response.

### 5. Feedback Mechanism
- **User Given**: As a user, I want to receive constructive feedback to improve my responses.
- **When**: Feedback is provided after each answer.
- **Outcome**: Feedback highlights strengths, weaknesses, and suggestions for improvement.

### 6. Resume-Based Answering
- **User Given**: As a user, I want the app to answer questions using my resume as a source.
- **When**: The user asks how the app would respond to a question based on the resume.
- **Outcome**: The app generates a response using relevant information from the resume, demonstrating potential answers.

---

## Test Document

### 1. File Upload Capability
- **Test Scenario**: Verify that users can upload job descriptions and resumes in various formats (e.g., PDF, DOCX).
- **Expected Outcome**: The app accepts the files, stores them securely, and they can be accessed for question generation.

### 2. Question Generation
- **Test Scenario**: Check if relevant interview questions are generated based on the uploaded job description and resume.
- **Expected Outcome**: The app generates a set of questions that align with the job requirements and the user's qualifications.

### 3. User Answer Interaction
- **Test Scenario**: Confirm that users can interactively answer the generated interview questions.
- **Expected Outcome**: Users should be able to submit answers without errors, and the answers are recorded in the system.

### 4. Answer Evaluation
- **Test Scenario**: Validate that the app evaluates the content and tone of user answers.
- **Expected Outcome**: Each answer is analyzed, and feedback is provided regarding content accuracy and tone appropriateness.

### 5. Feedback Mechanism
- **Test Scenario**: Ensure that users receive constructive feedback after each answer.
- **Expected Outcome**: Feedback should highlight areas for improvement and provide specific suggestions.

### 6. Resume-Based Answering
- **Test Scenario**: Test the app's ability to answer questions using the user's resume as a factual source.
- **Expected Outcome**: The app should generate accurate responses based on the resume, demonstrating potential answers to interview questions.