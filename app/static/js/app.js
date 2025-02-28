// app/static/js/app.js

// State management
let state = {
    sessionId: null,
    questions: [],
    currentQuestionIndex: 0,
    answers: [],
    evaluations: [],
    room: null,
    participant: null,
    isRecording: false,
    recognition: null
};

// DOM elements
const uploadSection = document.getElementById('upload-section');
const loadingSection = document.getElementById('loading-section');
const interviewSection = document.getElementById('interview-section');
const feedbackSection = document.getElementById('feedback-section');
const exampleSection = document.getElementById('example-section');
const summarySection = document.getElementById('summary-section');

const uploadForm = document.getElementById('upload-form');
const currentQuestion = document.getElementById('current-question');
const answerInput = document.getElementById('answer');
const answerBtn = document.getElementById('submit-answer');
const getExampleBtn = document.getElementById('get-example');
const nextQuestionBtn = document.getElementById('next-question');
const backToInterviewBtn = document.getElementById('back-to-interview');
const restartInterviewBtn = document.getElementById('restart-interview');

const scoreValue = document.getElementById('score-value');
const scoreBar = document.getElementById('score-bar');
const strengthsFeedback = document.getElementById('strengths-feedback');
const improvementsFeedback = document.getElementById('improvements-feedback');
const contentFeedback = document.getElementById('content-feedback');
const toneFeedback = document.getElementById('tone-feedback');
const exampleAnswer = document.getElementById('example-answer');

const averageScore = document.getElementById('average-score');
const averageScoreBar = document.getElementById('average-score-bar');
const overallStrengths = document.getElementById('overall-strengths');
const overallImprovements = document.getElementById('overall-improvements');

// Speech Recognition Setup
function setupSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.error('Speech recognition not supported');
        return false;
    }
    
    // Create speech recognition instance
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = true;
    state.recognition.interimResults = true;
    state.recognition.lang = 'en-US';
    
    // Add the mic button if not already present
    createMicButton();
    
    // Handle recognition results
    state.recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        
        if (finalTranscript) {
            // Append to textarea instead of replacing
            answerInput.value += ' ' + finalTranscript;
        }
    };
    
    state.recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        stopRecording();
    };
    
    state.recognition.onend = () => {
        stopRecording();
    };
    
    return true;
}

// Create and add microphone button
function createMicButton() {
    // Check if button already exists
    if (document.getElementById('mic-button')) {
        return;
    }
    
    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'mt-2';
    
    // Create mic button
    const micButton = document.createElement('button');
    micButton.id = 'mic-button';
    micButton.className = 'inline-flex items-center justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500';
    micButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd" /></svg> Speak Your Answer';
    
    micButton.addEventListener('click', toggleRecording);
    
    // Create recording status indicator
    const recordingStatus = document.createElement('span');
    recordingStatus.id = 'recording-status';
    recordingStatus.className = 'ml-3 text-sm hidden';
    recordingStatus.innerHTML = '<span class="inline-block h-3 w-3 rounded-full bg-red-500 animate-pulse mr-1"></span> Recording...';
    
    // Add elements to the DOM
    buttonContainer.appendChild(micButton);
    buttonContainer.appendChild(recordingStatus);
    
    // Insert after the answer textarea
    answerInput.parentNode.insertAdjacentElement('afterend', buttonContainer);
}

// Toggle recording state
function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

// Start recording
function startRecording() {
    if (!state.recognition) {
        setupSpeechRecognition();
    }
    
    if (state.recognition) {
        try {
            state.recognition.start();
            state.isRecording = true;
            
            // Update UI
            const micButton = document.getElementById('mic-button');
            const recordingStatus = document.getElementById('recording-status');
            
            if (micButton) {
                micButton.classList.add('bg-red-100');
                micButton.classList.add('text-red-700');
            }
            
            if (recordingStatus) {
                recordingStatus.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error starting speech recognition:', error);
        }
    }
}

// Stop recording
function stopRecording() {
    if (state.recognition && state.isRecording) {
        state.recognition.stop();
        state.isRecording = false;
        
        // Update UI
        const micButton = document.getElementById('mic-button');
        const recordingStatus = document.getElementById('recording-status');
        
        if (micButton) {
            micButton.classList.remove('bg-red-100');
            micButton.classList.remove('text-red-700');
        }
        
        if (recordingStatus) {
            recordingStatus.classList.add('hidden');
        }
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupSpeechRecognition();
});

function setupEventListeners() {
    // Handle form submission
    uploadForm.addEventListener('submit', handleDocumentUpload);
    
    // Answer submission
    answerBtn.addEventListener('click', handleAnswerSubmission);
    
    // Get example answer
    getExampleBtn.addEventListener('click', handleGetExample);
    
    // Next question
    nextQuestionBtn.addEventListener('click', handleNextQuestion);
    
    // Back to interview
    backToInterviewBtn.addEventListener('click', () => {
        exampleSection.classList.add('hidden');
        document.getElementById('interview-container').classList.remove('hidden');
    });
    
    // Restart interview
    restartInterviewBtn.addEventListener('click', handleRestartInterview);
}

// Handle document upload
async function handleDocumentUpload(e) {
    e.preventDefault();
    
    // Show loading section
    uploadSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    
    // Get form data
    const formData = new FormData();
    formData.append('resume', document.getElementById('resume').files[0]);
    formData.append('job_description', document.getElementById('job-description').files[0]);
    
    try {
        // Upload documents
        const response = await fetch('/upload-documents', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload documents');
        }
        
        const data = await response.json();
        state.sessionId = data.session_id;
        
        // Generate questions
        await generateQuestions();
        
        // Connect to room
        await connectToRoom(state.sessionId);
        
        // Show interview section
        loadingSection.classList.add('hidden');
        interviewSection.classList.remove('hidden');
        
        // Display first question
        displayQuestion(0);
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
        
        // Go back to upload section
        loadingSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
    }
}

// Generate interview questions
async function generateQuestions() {
    try {
        const response = await fetch('/generate-questions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: state.sessionId,
                num_questions: 5
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate questions');
        }
        
        const data = await response.json();
        state.questions = data.questions;
        
    } catch (error) {
        console.error('Error generating questions:', error);
        throw error;
    }
}

// Connect to LiveKit room
async function connectToRoom(sessionId) {
    try {
        const response = await fetch(`/session/${sessionId}`);
        if (!response.ok) {
            throw new Error('Failed to get session data');
        }
        
        // For this implementation, we're not actually connecting to LiveKit yet
        // In a real implementation, you would get a token and connect to the room
        console.log('Would connect to LiveKit room here');
        
    } catch (error) {
        console.error('Error connecting to room:', error);
        throw error;
    }
}

// Display current question
function displayQuestion(index) {
    if (index >= state.questions.length) {
        displaySummary();
        return;
    }
    
    state.currentQuestionIndex = index;
    const question = state.questions[index];
    
    currentQuestion.textContent = question;
    answerInput.value = '';
    
    document.getElementById('interview-container').classList.remove('hidden');
    feedbackSection.classList.add('hidden');
    exampleSection.classList.add('hidden');
}

// Handle answer submission
async function handleAnswerSubmission() {
    // If recording is active, stop it
    if (state.isRecording) {
        stopRecording();
    }
    
    const answer = answerInput.value.trim();
    
    if (!answer) {
        alert('Please provide an answer');
        return;
    }
    
    // Show loading indicator
    answerBtn.disabled = true;
    answerBtn.innerHTML = '<span class="spinner"></span> Evaluating...';
    
    try {
        const question = state.questions[state.currentQuestionIndex];
        console.log(`Submitting answer for evaluation - Question: "${question}"`);
        
        // Store answer
        state.answers.push({
            question,
            answer
        });
        
        // Evaluate answer
        const response = await fetch('/evaluate-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: state.sessionId,
                question,
                answer
            })
        });
        
        // Log raw response
        console.log("Response status:", response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error("Error response:", errorText);
            throw new Error(`Failed to evaluate answer: ${errorText}`);
        }
        
        const data = await response.json();
        console.log("Evaluation data:", data);
        
        const evaluation = data.evaluation;
        
        // Store evaluation
        state.evaluations.push(evaluation);
        
        // Display feedback
        displayFeedback(evaluation);
        
    } catch (error) {
        console.error('Error during evaluation:', error);
        alert('Error evaluating your answer. Please try again.');
    } finally {
        // Reset button state
        answerBtn.disabled = false;
        answerBtn.innerHTML = 'Submit Answer';
    }
}

// Display feedback
function displayFeedback(evaluation) {
    // Hide interview container
    document.getElementById('interview-container').classList.add('hidden');
    
    console.log("Received evaluation:", evaluation);
    
    // Set feedback values
    scoreValue.textContent = `${evaluation.score}/10`;
    scoreBar.style.width = `${evaluation.score * 10}%`;
    
    // Format strengths (handling both string and array formats)
    if (Array.isArray(evaluation.strengths)) {
        strengthsFeedback.textContent = evaluation.strengths.join(', ');
    } else {
        strengthsFeedback.textContent = evaluation.strengths || 'No specific strengths noted.';
    }
    
    // Format weaknesses/improvements (handling both string and array formats)
    if (Array.isArray(evaluation.weaknesses)) {
        improvementsFeedback.textContent = evaluation.weaknesses.join(', ');
    } else {
        improvementsFeedback.textContent = evaluation.weaknesses || 'No specific improvements suggested.';
    }
    
    // Set content and tone feedback from the detailed feedback field
    contentFeedback.textContent = evaluation.feedback || 'No content feedback available.';
    toneFeedback.textContent = evaluation.example_improvement || 'No tone feedback available.';
    
    // Show feedback section
    feedbackSection.classList.remove('hidden');
    
    // If this is the last question, change button text
    if (state.currentQuestionIndex >= state.questions.length - 1) {
        nextQuestionBtn.textContent = 'See Summary';
    } else {
        nextQuestionBtn.textContent = 'Next Question';
    }
}

// Markdown Formatting for Example Answers
function formatExampleAnswer(answer) {
    // Check if answer is a valid object or string
    if (!answer) return '';

    // If answer is a string, try to parse it
    if (typeof answer === 'string') {
        try {
            answer = JSON.parse(answer);
        } catch {
            // If parsing fails, return the original string
            return answer;
        }
    }

    // Destructure answer components or use default values
    const {
        title = 'Interview Answer',
        professionalExperience = '',
        keyHighlights = [],
        conclusion = ''
    } = answer;

    // Build markdown formatted answer
    let formattedAnswer = `# ${title}\n\n`;
    
    // Professional Experience Section
    if (professionalExperience) {
        formattedAnswer += `## Professional Experience\n${professionalExperience}\n\n`;
    }

    // Key Highlights Section
    if (keyHighlights.length > 0) {
        formattedAnswer += `## Key Highlights\n`;
        keyHighlights.forEach((highlight, index) => {
            formattedAnswer += `${index + 1}. **${highlight.title || 'Achievement'}**\n`;
            if (highlight.details && highlight.details.length > 0) {
                highlight.details.forEach(detail => {
                    formattedAnswer += `   - ${detail}\n`;
                });
            }
            formattedAnswer += '\n';
        });
    }

    // Conclusion Section
    if (conclusion) {
        formattedAnswer += `## Conclusion\n${conclusion}`;
    }

    return formattedAnswer;
}

// Update example answer display to use markdown formatting
function displayExampleAnswer(answer) {
    const formattedAnswer = formatExampleAnswer(answer);
    
    // Convert markdown to HTML for display
    const converter = new showdown.Converter();
    const htmlContent = converter.makeHtml(formattedAnswer);
    
    exampleAnswer.innerHTML = htmlContent;
}

// Handle getting example answer
async function handleGetExample() {
    try {
        const question = state.questions[state.currentQuestionIndex];
        
        // Get example answer
        const response = await fetch('/generate-example-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: state.sessionId,
                question
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get example answer');
        }
        
        const data = await response.json();
        
        // Hide interview container
        document.getElementById('interview-container').classList.add('hidden');
        
        // Set example answer
        displayExampleAnswer(data.answer);
        
        // Show example section
        exampleSection.classList.remove('hidden');
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error: ' + error.message);
    }
}

// Handle moving to next question
function handleNextQuestion() {
    // Move to next question or summary
    if (state.currentQuestionIndex >= state.questions.length - 1) {
        displaySummary();
    } else {
        displayQuestion(state.currentQuestionIndex + 1);
    }
}

// Display interview summary
function displaySummary() {
    // Hide other sections
    document.getElementById('interview-container').classList.add('hidden');
    feedbackSection.classList.add('hidden');
    exampleSection.classList.add('hidden');
    
    // Calculate average score
    const totalScore = state.evaluations.reduce((sum, eval) => sum + eval.score, 0);
    const avgScore = totalScore / state.evaluations.length;
    
    // Set summary values
    averageScore.textContent = `${avgScore.toFixed(1)}/10`;
    averageScoreBar.style.width = `${avgScore * 10}%`;
    
    // Clear previous lists
    overallStrengths.innerHTML = '';
    overallImprovements.innerHTML = '';
    
    // Compile strengths and improvement areas
    const strengths = new Set();
    const improvements = new Set();
    
    state.evaluations.forEach(eval => {
        if (eval.strengths) {
            strengths.add(eval.strengths);
        }
        if (eval.weaknesses) {
            improvements.add(eval.weaknesses);
        }
    });
    
    // Add to lists
    strengths.forEach(strength => {
        const li = document.createElement('li');
        li.textContent = strength;
        overallStrengths.appendChild(li);
    });
    
    improvements.forEach(improvement => {
        const li = document.createElement('li');
        li.textContent = improvement;
        overallImprovements.appendChild(li);
    });
    
    // Show summary section
    summarySection.classList.remove('hidden');
}

// Handle restarting interview
function handleRestartInterview() {
    // Reset state
    state = {
        sessionId: null,
        questions: [],
        currentQuestionIndex: 0,
        answers: [],
        evaluations: [],
        room: null,
        participant: null,
        isRecording: false,
        recognition: null
    };
    
    // Hide sections
    interviewSection.classList.add('hidden');
    summarySection.classList.add('hidden');
    
    // Clear form fields
    document.getElementById('resume').value = '';
    document.getElementById('job-description').value = '';
    
    // Show upload section
    uploadSection.classList.remove('hidden');
}