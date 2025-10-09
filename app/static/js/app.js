// app/static/js/app.js

// State management
function createInitialVoiceState() {
    return {
        peer: null,
        dataChannel: null,
        localStream: null,
        remoteStream: null,
        transcriptBuffer: '',
    };
}

function createInitialState() {
    return {
        sessionId: null,
        questions: [],
        currentQuestionIndex: 0,
        answers: [],
        evaluations: [],
        room: null,
        participant: null,
        isRecording: false,
        recognition: null,
        voice: createInitialVoiceState(),
    };
}

let state = createInitialState();

// DOM elements
const uploadSection = document.getElementById('upload-section');
const loadingSection = document.getElementById('loading-section');
const interviewSection = document.getElementById('interview-section');
const feedbackSection = document.getElementById('feedback-section');
const exampleSection = document.getElementById('example-section');
const summarySection = document.getElementById('summary-section');
const interviewContainer = document.getElementById('interview-container');
const resumeActions = document.getElementById('resume-actions');
const resumeSessionBtn = document.getElementById('resume-session');
const clearSessionBtn = document.getElementById('clear-session');

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
const exampleQuestion = document.getElementById('example-question');

const averageScore = document.getElementById('average-score');
const averageScoreBar = document.getElementById('average-score-bar');
const overallStrengths = document.getElementById('overall-strengths');
const overallImprovements = document.getElementById('overall-improvements');

const startVoiceBtn = document.getElementById('start-voice');
const stopVoiceBtn = document.getElementById('stop-voice');
const voiceStatus = document.getElementById('voice-status');
const voiceTranscript = document.getElementById('voice-transcript');
const voiceAudio = document.getElementById('voice-audio');

const voiceStatusClasses = {
    idle: 'text-gray-500',
    pending: 'text-amber-600',
    live: 'text-green-600',
    error: 'text-red-600'
};

function setVoiceControls(active) {
    if (startVoiceBtn) {
        startVoiceBtn.classList.toggle('hidden', active);
    }
    if (stopVoiceBtn) {
        stopVoiceBtn.classList.toggle('hidden', !active);
    }
}

function setVoiceEnabled(enabled) {
    if (!startVoiceBtn) {
        return;
    }
    startVoiceBtn.disabled = !enabled;
    startVoiceBtn.classList.toggle('opacity-50', !enabled);
    startVoiceBtn.classList.toggle('cursor-not-allowed', !enabled);
}

function updateVoiceStatus(message, tone = 'idle') {
    if (!voiceStatus) {
        return;
    }
    const toneClass = voiceStatusClasses[tone] || voiceStatusClasses.idle;
    voiceStatus.className = `text-sm font-medium ${toneClass}`;
    voiceStatus.textContent = message;
}

function clearVoiceTranscript() {
    if (!voiceTranscript) {
        return;
    }
    if (state && state.voice) {
        state.voice.transcriptBuffer = '';
    }
    voiceTranscript.dataset.empty = 'true';
    voiceTranscript.innerHTML = '<p class="text-xs text-gray-500">Voice transcripts will appear here once the realtime session begins.</p>';
}

function appendVoiceMessage(role, message) {
    if (!voiceTranscript || !message) {
        return;
    }

    const text = message.trim();
    if (!text) {
        return;
    }

    if (voiceTranscript.dataset.empty === 'true') {
        voiceTranscript.innerHTML = '';
        delete voiceTranscript.dataset.empty;
    }

    const wrapper = document.createElement('div');

    if (role === 'agent') {
        wrapper.className = 'bg-indigo-50 border border-indigo-100 text-indigo-800 text-sm rounded-lg p-3';
    } else if (role === 'user') {
        wrapper.className = 'bg-white border border-gray-200 text-gray-800 text-sm rounded-lg p-3';
    } else {
        wrapper.className = 'text-xs text-gray-500';
    }

    if (role === 'agent' || role === 'user') {
        const label = document.createElement('div');
        label.className = 'text-xs uppercase tracking-wide font-semibold mb-1';
        label.textContent = role === 'agent' ? 'Coach' : 'You';
        wrapper.appendChild(label);

        const content = document.createElement('p');
        content.textContent = text;
        wrapper.appendChild(content);
    } else {
        wrapper.textContent = text;
    }

    voiceTranscript.appendChild(wrapper);
    voiceTranscript.scrollTop = voiceTranscript.scrollHeight;
}

function handleVoiceEvent(event) {
    if (!event || !event.type) {
        return;
    }

    switch (event.type) {
        case 'response.output_text.delta': {
            const delta = event.delta || event.text || '';
            state.voice.transcriptBuffer += delta;
            break;
        }
        case 'response.output_text.done':
        case 'response.completed': {
            if (state.voice.transcriptBuffer.trim()) {
                appendVoiceMessage('agent', state.voice.transcriptBuffer.trim());
            }
            state.voice.transcriptBuffer = '';
            break;
        }
        case 'response.error': {
            const errorMessage = (event.error && event.error.message) || 'Realtime agent reported an error.';
            appendVoiceMessage('system', `Warning: ${errorMessage}`);
            updateVoiceStatus('Error', 'error');
            state.voice.transcriptBuffer = '';
            break;
        }
        case 'conversation.item.input_audio_transcription.completed':
        case 'input_audio_buffer.speech_transcribed': {
            const transcriptText = event.transcript || event.text || '';
            if (transcriptText) {
                appendVoiceMessage('user', transcriptText);
            }
            break;
        }
        default: {
            if (event.type && event.type.startsWith('response.audio')) {
                return;
            }
            if (event.type !== 'response.created' && event.type !== 'response.output_text.created') {
                console.debug('Voice event:', event);
            }
        }
    }
}

async function startVoiceInterview() {
    if (!state.sessionId) {
        alert('Upload your documents to start a practice session before enabling voice coaching.');
        return;
    }

    if (state.voice.peer) {
        console.debug('Voice interview already active');
        return;
    }

    setVoiceControls(true);
    updateVoiceStatus('Connecting...', 'pending');
    if (voiceTranscript && voiceTranscript.dataset.empty !== 'true') {
        appendVoiceMessage('system', '--- Starting new voice session ---');
    }

    try {
        const response = await fetch('/voice/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: state.sessionId
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Failed to initialize voice session');
        }

        const data = await response.json();
        const { client_secret: clientSecret, model, url } = data;

        if (!clientSecret) {
            throw new Error('Realtime session did not return a client secret');
        }

        const peer = new RTCPeerConnection();
        state.voice.peer = peer;

        const dataChannel = peer.createDataChannel('oai-events');
        state.voice.dataChannel = dataChannel;

        dataChannel.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                handleVoiceEvent(payload);
            } catch (err) {
                console.debug('Non-JSON voice event payload:', event.data);
            }
        };

        dataChannel.onopen = () => {
            updateVoiceStatus('Live', 'live');
            const openingQuestion =
                state.questions[state.currentQuestionIndex] ||
                state.questions[0] ||
                'Tell me about yourself.';

            try {
                dataChannel.send(JSON.stringify({
                    type: 'response.create',
                    response: {
                        modalities: ['audio', 'text'],
                        instructions: `Begin the interview. Greet the candidate and ask: "${openingQuestion}". Wait for their response before giving concise feedback.`,
                    }
                }));
            } catch (sendError) {
                console.debug('Failed to send initial realtime instruction:', sendError);
            }
        };

        dataChannel.onclose = () => {
            if (peer.connectionState !== 'closed') {
                updateVoiceStatus('Voice channel closed', 'idle');
            }
        };

        peer.onconnectionstatechange = () => {
            if (peer.connectionState === 'connected') {
                updateVoiceStatus('Live', 'live');
            } else if (['disconnected', 'failed'].includes(peer.connectionState)) {
                updateVoiceStatus('Disconnected', 'error');
                stopVoiceInterview({ silent: true, preserveStatus: true });
            }
        };

        const localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.voice.localStream = localStream;
        localStream.getTracks().forEach(track => peer.addTrack(track, localStream));

        peer.ontrack = (event) => {
            if (!voiceAudio) {
                return;
            }

            const [remoteStream] = event.streams;
            if (voiceAudio.srcObject !== remoteStream) {
                voiceAudio.srcObject = remoteStream;
                voiceAudio.classList.remove('hidden');
                voiceAudio.play().catch(err => console.debug('Autoplay blocked:', err));
            }
        };

        const offer = await peer.createOffer();
        await peer.setLocalDescription(offer);

        const realtimeUrl = `${url}?model=${encodeURIComponent(model)}`;
        const sdpResponse = await fetch(realtimeUrl, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${clientSecret}`,
                'Content-Type': 'application/sdp',
                'OpenAI-Beta': 'realtime=v1'
            },
            body: offer.sdp
        });

        if (!sdpResponse.ok) {
            const errText = await sdpResponse.text();
            throw new Error(errText || 'Failed to negotiate realtime session');
        }

        const answer = await sdpResponse.text();
        await peer.setRemoteDescription({ type: 'answer', sdp: answer });
        updateVoiceStatus('Live', 'live');
    } catch (error) {
        console.error('Voice session error:', error);
        appendVoiceMessage('system', `Voice session error: ${error.message}`);
        updateVoiceStatus('Connection failed', 'error');
        stopVoiceInterview({ silent: true, preserveStatus: true });
        setVoiceControls(false);
    }
}

function stopVoiceInterview(options = {}) {
    const { silent = false, preserveStatus = false } = options;

    if (state.voice.dataChannel) {
        try {
            state.voice.dataChannel.close();
        } catch (error) {
            console.debug('Error closing realtime data channel:', error);
        }
    }

    if (state.voice.peer) {
        try {
            state.voice.peer.close();
        } catch (error) {
            console.debug('Error closing realtime peer connection:', error);
        }
    }

    if (state.voice.localStream) {
        state.voice.localStream.getTracks().forEach(track => track.stop());
    }

    if (voiceAudio) {
        voiceAudio.srcObject = null;
        voiceAudio.classList.add('hidden');
    }

    state.voice = createInitialVoiceState();

    if (!preserveStatus) {
        updateVoiceStatus(silent ? 'Offline' : 'Voice session ended', 'idle');
    }

    setVoiceControls(false);
}

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
    clearVoiceTranscript();
    updateVoiceStatus('Offline', 'idle');
    setVoiceControls(false);
    setVoiceEnabled(false);
    updateResumeControlsVisibility();
});

window.addEventListener('beforeunload', () => {
    stopVoiceInterview({ silent: true, preserveStatus: true });
});

function setupEventListeners() {
    if (resumeSessionBtn) {
        resumeSessionBtn.addEventListener('click', (event) => {
            event.preventDefault();
            resumeSavedSession();
        });
    }

    if (clearSessionBtn) {
        clearSessionBtn.addEventListener('click', async (event) => {
            event.preventDefault();
            await clearSavedSession();
        });
    }

    // Handle form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleDocumentUpload);
    }

    // Answer submission
    if (answerBtn) {
        answerBtn.addEventListener('click', handleAnswerSubmission);
    }

    // Get example answer
    if (getExampleBtn) {
        getExampleBtn.addEventListener('click', handleGetExample);
    }

    // Next question
    if (nextQuestionBtn) {
        nextQuestionBtn.addEventListener('click', handleNextQuestion);
    }

    // Back to interview
    if (backToInterviewBtn) {
        backToInterviewBtn.addEventListener('click', () => {
            exampleSection.classList.add('hidden');
            if (exampleQuestion) {
                exampleQuestion.textContent = '';
                exampleQuestion.classList.add('hidden');
            }
            if (interviewContainer) {
                interviewContainer.classList.remove('hidden');
            }
        });
    }

    // Restart interview
    if (restartInterviewBtn) {
        restartInterviewBtn.addEventListener('click', handleRestartInterview);
    }

    if (startVoiceBtn) {
        startVoiceBtn.addEventListener('click', startVoiceInterview);
    }

    if (stopVoiceBtn) {
        stopVoiceBtn.addEventListener('click', () => stopVoiceInterview());
    }
}

function updateResumeControlsVisibility() {
    if (!resumeActions) {
        return;
    }
    const savedId = localStorage.getItem('interviewSessionId');
    resumeActions.classList.toggle('hidden', !savedId);
}

async function resumeSavedSession() {
    const savedSessionId = localStorage.getItem('interviewSessionId');
    if (!savedSessionId) {
        alert('No saved session was found.');
        updateResumeControlsVisibility();
        return;
    }

    try {
        stopVoiceInterview({ silent: true });
        clearVoiceTranscript();
        updateVoiceStatus('Offline', 'idle');
        setVoiceControls(false);
        setVoiceEnabled(false);

        if (uploadSection) {
            uploadSection.classList.add('hidden');
        }
        if (loadingSection) {
            loadingSection.classList.remove('hidden');
        }

        const response = await fetch(`/session/${savedSessionId}`);
        if (!response.ok) {
            throw new Error('Failed to load saved session');
        }

        const data = await response.json();

        state = createInitialState();
        state.sessionId = data.session_id;
        state.questions = data.questions || [];
        state.answers = data.answers || [];
        state.evaluations = data.evaluations || [];

        const persistedIndex = typeof data.current_question_index === 'number'
            ? data.current_question_index
            : state.answers.length;
        const clampedIndex = Math.max(0, Math.min(persistedIndex, state.questions.length));
        state.currentQuestionIndex = clampedIndex >= state.questions.length && state.questions.length > 0
            ? state.questions.length - 1
            : clampedIndex;

        if (loadingSection) {
            loadingSection.classList.add('hidden');
        }
        if (interviewSection) {
            interviewSection.classList.remove('hidden');
        }

        setVoiceControls(false);
        const hasQuestions = state.questions.length > 0;
        setVoiceEnabled(hasQuestions);
        updateVoiceStatus(hasQuestions ? 'Ready for voice coaching' : 'Offline', 'idle');
        clearVoiceTranscript();

        if (!hasQuestions) {
            if (interviewContainer) {
                interviewContainer.classList.remove('hidden');
            }
            currentQuestion.textContent = 'No questions available yet. Generate questions to begin.';
            feedbackSection.classList.add('hidden');
            exampleSection.classList.add('hidden');
            summarySection.classList.add('hidden');
            updateResumeControlsVisibility();
            return;
        }

        if (clampedIndex >= state.questions.length) {
            displaySummary();
        } else {
            displayQuestion(clampedIndex);
            if (state.evaluations.length > 0) {
                nextQuestionBtn.textContent = clampedIndex >= state.questions.length - 1 ? 'See Summary' : 'Next Question';
            }
        }

        updateResumeControlsVisibility();
    } catch (error) {
        console.error('Error resuming session:', error);
        alert('Unable to resume the saved session. It may have expired or been removed.');
        localStorage.removeItem('interviewSessionId');
        updateResumeControlsVisibility();
        if (loadingSection) {
            loadingSection.classList.add('hidden');
        }
        if (uploadSection) {
            uploadSection.classList.remove('hidden');
        }
    }
}

async function clearSavedSession() {
    const savedSessionId = localStorage.getItem('interviewSessionId');
    if (!savedSessionId) {
        updateResumeControlsVisibility();
        return;
    }

    const confirmed = window.confirm('This will permanently remove your saved session. Continue?');
    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/session/${savedSessionId}`, { method: 'DELETE' });
        if (!response.ok && response.status !== 404) {
            throw new Error('Failed to delete saved session');
        }
    } catch (error) {
        console.error('Error clearing saved session:', error);
        alert('Unable to clear the saved session right now. Please try again.');
        return;
    }

    localStorage.removeItem('interviewSessionId');
    updateResumeControlsVisibility();
    if (state.sessionId === savedSessionId) {
        handleRestartInterview();
    }
}

// Handle document upload
async function handleDocumentUpload(e) {
    e.preventDefault();
    
    const resumeInput = document.getElementById('resume');
    const jobFileInput = document.getElementById('job-description');
    const jobTextInput = document.getElementById('job-description-text');

    const resumeFile = resumeInput.files[0];
    const jobFile = jobFileInput.files[0];
    const jobText = jobTextInput.value.trim();

    if (!resumeFile) {
        alert('Please upload your resume to continue.');
        return;
    }

    if (!jobFile && !jobText) {
        alert('Please upload a job description file or paste the job description text.');
        return;
    }

    // Show loading section
    uploadSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    
    // Get form data
    const formData = new FormData();
    formData.append('resume', resumeFile);
    if (jobFile) {
        formData.append('job_description', jobFile);
    }
    if (jobText) {
        formData.append('job_description_text', jobText);
    }
    
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
        localStorage.setItem('interviewSessionId', state.sessionId);
        updateResumeControlsVisibility();
        
        // Generate questions
        await generateQuestions();

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
        setVoiceEnabled(true);
        updateVoiceStatus('Ready for voice coaching', 'idle');
        clearVoiceTranscript();
        
    } catch (error) {
        console.error('Error generating questions:', error);
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
    
    if (interviewContainer) {
        interviewContainer.classList.remove('hidden');
    }
    feedbackSection.classList.add('hidden');
    exampleSection.classList.add('hidden');
    if (exampleQuestion) {
        exampleQuestion.textContent = '';
        exampleQuestion.classList.add('hidden');
    }
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
    
    if (typeof showdown === 'undefined') {
        // Gracefully fall back to plain text if showdown failed to load
        exampleAnswer.textContent = formattedAnswer;
        return;
    }

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
        if (exampleQuestion) {
            exampleQuestion.textContent = `Question: ${question}`;
            exampleQuestion.classList.remove('hidden');
        }
        
        // Set example answer
        displayExampleAnswer(data.answer);
        
        // Show example section
        exampleSection.classList.remove('hidden');
        exampleSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
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
    if (interviewContainer) {
        interviewContainer.classList.add('hidden');
    }
    feedbackSection.classList.add('hidden');
    exampleSection.classList.add('hidden');
    if (exampleQuestion) {
        exampleQuestion.textContent = '';
        exampleQuestion.classList.add('hidden');
    }
    
    // Calculate average score
    const totalScore = state.evaluations.reduce((sum, eval) => sum + (eval.score || 0), 0);
    const evaluationCount = state.evaluations.length;
    const avgScore = evaluationCount > 0 ? totalScore / evaluationCount : 0;
    
    // Set summary values
    if (evaluationCount > 0) {
        averageScore.textContent = `${avgScore.toFixed(1)}/10`;
        averageScoreBar.style.width = `${Math.min(100, Math.max(0, avgScore * 10))}%`;
    } else {
        averageScore.textContent = 'N/A';
        averageScoreBar.style.width = '0%';
    }
    
    // Clear previous lists
    overallStrengths.innerHTML = '';
    overallImprovements.innerHTML = '';
    
    // Compile strengths and improvement areas
    const strengths = new Set();
    const improvements = new Set();
    
    state.evaluations.forEach(eval => {
        if (eval.strengths) {
            strengths.add(Array.isArray(eval.strengths) ? eval.strengths.join(', ') : eval.strengths);
        }
        if (eval.weaknesses) {
            improvements.add(Array.isArray(eval.weaknesses) ? eval.weaknesses.join(', ') : eval.weaknesses);
        }
        if (eval.improvements && !eval.weaknesses) {
            improvements.add(Array.isArray(eval.improvements) ? eval.improvements.join(', ') : eval.improvements);
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
    stopVoiceInterview({ silent: true });

    // Reset state
    state = createInitialState();
    
    // Hide sections
    interviewSection.classList.add('hidden');
    summarySection.classList.add('hidden');
    
    // Clear form fields
    document.getElementById('resume').value = '';
    document.getElementById('job-description').value = '';
    document.getElementById('job-description-text').value = '';
    
    setVoiceEnabled(false);
    clearVoiceTranscript();
    updateVoiceStatus('Offline', 'idle');
    localStorage.removeItem('interviewSessionId');
    updateResumeControlsVisibility();

    // Show upload section
    uploadSection.classList.remove('hidden');
}
