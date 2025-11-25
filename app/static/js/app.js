// app/static/js/app.js

// State management
function createInitialVoiceState() {
    return {
        peer: null,
        dataChannel: null,
        localStream: null,
        remoteStream: null,
        transcriptBuffer: '',
        transcriptsByIndex: {},
        messages: [],
        agentStream: null,
        userStream: null,
        activityMonitor: null,
        browserAsrActive: false,
        // True while the agent is speaking; used to suppress browser ASR echo
        agentSpeaking: false,
        // When true, browser ASR results are ignored (set during agent audio)
        suppressBrowserAsr: false,
        // Normalized text of the most recent finalized user message to avoid dupes
        lastUserFinalNormalized: '',
        // Remember who last completed a turn so we can choose whether to
        // start a new bubble or continue the previous one.
        lastFinalSpeaker: '',
        config: {
            // Default OFF: rely on server-side transcription unless explicitly enabled
            useBrowserAsr: false,
            showMetadata: false,
        },
    };
}

function createInitialState() {
    return {
        sessionId: null,
        sessionName: null,
        questions: [],
        currentQuestionIndex: 0,
        answers: [],
        evaluations: [],
        reviewFlags: {},
        coachLevel: 'level_1',
        // When true, displayFeedback will be shown once after resume if available
        resumeShowFeedbackOnce: false,
        resumeText: '',
        jobDescText: '',
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
const sessionNameEl = document.getElementById('session-name');
const questionPosEl = document.getElementById('question-position');
const docsPanel = document.getElementById('docs-panel');
const viewDocsBtn = document.getElementById('view-docs');
const resumeDocEl = document.getElementById('resume-doc');
const jobDocEl = document.getElementById('jobdoc-doc');
const resumeActions = document.getElementById('resume-actions');
// App bar controls
const newInterviewBtn = document.getElementById('global-new-interview');
const openSessionsBtn = document.getElementById('global-sessions');
const openSettingsBtn = document.getElementById('global-settings');
// Manual answer UI controls (hidden during live voice)
const answerLabel = document.querySelector('label[for="answer"]');
const resumeSessionBtn = document.getElementById('resume-session');
const clearSessionBtn = document.getElementById('clear-session');
const sessionsSelect = document.getElementById('saved-sessions');
const renameSessionBtn = document.getElementById('rename-session');
const renameSessionInput = document.getElementById('rename-session-input');
const sessionsCount = document.getElementById('sessions-count');
const switchSessionsSelect = document.getElementById('switch-sessions');
const switchSessionBtn = document.getElementById('switch-session');

const uploadForm = document.getElementById('upload-form');
const currentQuestion = document.getElementById('current-question');
const customQuestionInput = document.getElementById('custom-question-input');
const addCustomQuestionBtn = document.getElementById('add-custom-question');
const clearCustomQuestionBtn = document.getElementById('clear-custom-question');
const customQuestionStatus = document.getElementById('custom-question-status');
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
const feedbackUserTranscriptWrap = document.getElementById('feedback-user-transcript-wrap');
const feedbackUserTranscript = document.getElementById('feedback-user-transcript');
const feedbackCoachVoiceWrap = document.getElementById('feedback-coach-voice-wrap');
const feedbackCoachVoice = document.getElementById('feedback-coach-voice');
const feedbackTypedAnswerWrap = document.getElementById('feedback-typed-answer-wrap');
const feedbackTypedAnswer = document.getElementById('feedback-typed-answer');
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
const voiceTranscriptFreeze = document.getElementById('voice-transcript-freeze');
const voiceAudio = document.getElementById('voice-audio');
const voiceActivityIndicator = document.getElementById('voice-activity-indicator');
const voiceActivityDot = voiceActivityIndicator
    ? voiceActivityIndicator.querySelector('[data-indicator-dot]')
    : null;
const voiceActivityLabel = voiceActivityIndicator
    ? voiceActivityIndicator.querySelector('[data-indicator-label]')
    : null;
const toggleBrowserAsr = document.getElementById('toggle-browser-asr');
const toggleShowMetadata = document.getElementById('toggle-show-metadata');
const exportTranscriptBtn = document.getElementById('export-transcript');
const voiceSelect = document.getElementById('voice-select');
const voicePreviewBtn = document.getElementById('voice-preview');
const voiceSaveBtn = document.getElementById('voice-save');
const voicePreviewAudio = document.getElementById('voice-preview-audio');
// Coaching level controls
const coachLevelSelect = document.getElementById('coach-level-select');
const coachLevelSaveBtn = document.getElementById('coach-level-save');
// Voice submission button (parity with typed Submit)
const submitVoiceBtn = document.getElementById('submit-voice-answer');
const muteVoiceBtn = document.getElementById('mute-voice');
// Question rail & drawer
const questionRailList = document.getElementById('question-rail-list');
const questionDrawer = document.getElementById('question-drawer');
const questionDrawerList = document.getElementById('question-drawer-list');
const openQuestionDrawerBtn = document.getElementById('open-question-drawer');
const closeQuestionDrawerBtn = document.getElementById('close-question-drawer');
// Footer controls
const prevQuestionBtn = document.getElementById('prev-question');
const markReviewBtn = document.getElementById('mark-review');
const nextQuestionFooterBtn = document.getElementById('next-question-footer');
// Sessions modal
const sessionsModal = document.getElementById('sessions-modal');
const sessionsSearch = document.getElementById('sessions-search');
const sessionsRefresh = document.getElementById('sessions-refresh');
const sessionsModalSelect = document.getElementById('sessions-modal-select');
const sessionsLoadBtn = document.getElementById('sessions-load');
const sessionsRenameBtn = document.getElementById('sessions-rename');
const sessionsDeleteBtn = document.getElementById('sessions-delete');
const sessionsRenameInput = document.getElementById('sessions-rename-input');
const sessionsCloseBtn = document.getElementById('close-sessions');
// Voice settings drawer
const openVoiceSettingsBtn = document.getElementById('open-voice-settings');
const voiceSettingsDrawer = document.getElementById('voice-settings-drawer');
const closeVoiceSettingsBtn = document.getElementById('close-voice-settings');
const toggleBrowserAsr2 = document.getElementById('toggle-browser-asr-2');
const toggleShowMetadata2 = document.getElementById('toggle-show-metadata-2');
const coachLevelSelect2 = document.getElementById('coach-level-select-2');
const coachLevelSaveBtn2 = document.getElementById('coach-level-save-2');
const voiceSelect2 = document.getElementById('voice-select-2');
const voicePreviewBtn2 = document.getElementById('voice-preview-2');
const voiceSaveBtn2 = document.getElementById('voice-save-2');
const voicePreviewAudio2 = document.getElementById('voice-preview-audio-2');
const voiceSelect2Status = document.getElementById('voice-select-2-status');
const voiceSelect2Retry = document.getElementById('voice-select-2-retry');

const voiceStatusClasses = {
    idle: 'text-gray-500',
    pending: 'text-amber-600',
    live: 'text-green-600',
    error: 'text-red-600'
};

const baseVoiceActivityDotClass = 'inline-flex h-2.5 w-2.5 rounded-full transition';
const voiceActivityModes = {
    idle: { dot: 'bg-gray-300', label: 'Mic idle' },
    listening: { dot: 'bg-amber-400', label: 'Listening…' },
    speaking: { dot: 'bg-green-500 animate-pulse', label: 'Hearing you…' },
    muted: { dot: 'bg-red-500', label: 'Mic blocked' },
    unsupported: { dot: 'bg-gray-400', label: 'Mic level unavailable' },
};
let voiceActivityState = 'idle';
let customQuestionStatusTimer = null;
let customQuestionBound = false;
const feedbackNoiseTokens = new Set([
    'Unable to parse structured feedback',
    'No specific strengths noted.',
    'No specific improvements suggested.',
    'No content feedback available.',
]);

function setVoiceControls(active) {
    if (startVoiceBtn) {
        startVoiceBtn.classList.toggle('hidden', active);
    }
    if (stopVoiceBtn) {
        stopVoiceBtn.classList.toggle('hidden', !active);
    }
}

// Toggle layout between typed/manual vs. live voice
function setVoiceLayout(isLive) {
    // Hide manual input controls while voice is live
    if (answerLabel) answerLabel.classList.toggle('hidden', isLive);
    if (answerInput) answerInput.classList.toggle('hidden', isLive);
    if (answerBtn) answerBtn.classList.toggle('hidden', isLive);
    if (getExampleBtn) getExampleBtn.classList.toggle('hidden', isLive);
    const micButtonEl = document.getElementById('mic-button');
    if (micButtonEl) {
        const container = micButtonEl.parentElement || micButtonEl;
        container.classList.toggle('hidden', isLive);
    }
    // Expand transcript viewport while live for better readability
    if (voiceTranscript) {
        voiceTranscript.classList.toggle('max-h-64', !isLive);
        voiceTranscript.classList.toggle('max-h-96', isLive);
    }
    // Toggle visibility of pre-call settings and inline mute
    const voicePre = document.getElementById('voice-settings-pre');
    if (voicePre) voicePre.classList.toggle('hidden', isLive);
    if (muteVoiceBtn) muteVoiceBtn.classList.toggle('hidden', !isLive);
    // Re-evaluate whether the voice transcript is ready to submit
    try { updateVoiceSubmitAvailability(); } catch (_) {}
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
        state.voice.agentStream = null;
        state.voice.userStream = null;
        state.voice.transcriptsByIndex = {};
        state.voice.messages = [];
    }
    voiceTranscript.dataset.empty = 'true';
    voiceTranscript.innerHTML = '<p class="text-xs text-gray-500">Voice transcripts will appear here once the realtime session begins.</p>';
    setVoiceActivityIndicator('idle');
    try { updateVoiceSubmitAvailability(); } catch (_) {}
}

function scrollVoiceTranscriptToBottom() {
    if (!voiceTranscript) return;
    const frozen = voiceTranscript.dataset.freeze === 'true';
    if (frozen) return;
    voiceTranscript.scrollTop = voiceTranscript.scrollHeight;
}

const voiceRoleToBackend = {
    agent: 'coach',
    coach: 'coach',
    user: 'candidate',
    candidate: 'candidate',
    system: 'system',
};

const voiceRoleToDisplay = {
    coach: 'agent',
    candidate: 'user',
};

function findTextCandidate(input, depth = 0, seen = new Set()) {
    if (!input || depth > 4) {
        return '';
    }
    if (typeof input === 'string') {
        const trimmed = input.trim();
        if (trimmed && trimmed.length <= 4000) {
            return trimmed;
        }
        return '';
    }
    if (typeof input !== 'object') {
        return '';
    }
    if (seen.has(input)) {
        return '';
    }
    seen.add(input);

    const prioritizedKeys = ['transcript', 'text', 'value', 'caption', 'utterance'];
    for (const key of prioritizedKeys) {
        if (typeof input[key] === 'string') {
            const candidate = input[key].trim();
            if (candidate) {
                return candidate;
            }
        }
    }

    const collections = Array.isArray(input) ? input : Object.values(input);
    for (const entry of collections) {
        const found = findTextCandidate(entry, depth + 1, seen);
        if (found) {
            return found;
        }
    }

    return '';
}

function extractTranscriptFromRealtimeItem(item) {
    if (!item || typeof item !== 'object') {
        return '';
    }

    if (typeof item.formatted === 'string') {
        const formattedPlain = item.formatted.trim();
        if (formattedPlain) {
            return formattedPlain;
        }
    }
    if (item.formatted && typeof item.formatted === 'object') {
        const formattedTranscript =
            item.formatted.transcript || item.formatted.text || item.formatted.value || '';
        if (typeof formattedTranscript === 'string' && formattedTranscript.trim()) {
            return formattedTranscript.trim();
        }
        if (Array.isArray(item.formatted.messages)) {
            for (const message of item.formatted.messages) {
                const candidate = extractTranscriptFromRealtimeItem(message);
                if (candidate) {
                    return candidate;
                }
            }
        }
    }

    if (Array.isArray(item.content)) {
        for (const element of item.content) {
            const candidate = extractTranscriptFromRealtimeItem(element);
            if (candidate) {
                return candidate;
            }
        }
    }

    const direct = findTextCandidate(item);
    return direct;
}

function setVoiceActivityIndicator(mode) {
    if (!voiceActivityIndicator) {
        return;
    }
    const config = voiceActivityModes[mode] || voiceActivityModes.idle;
    voiceActivityState = mode;
    if (voiceActivityDot) {
        voiceActivityDot.className = `${baseVoiceActivityDotClass} ${config.dot}`;
    }
    if (voiceActivityLabel) {
        voiceActivityLabel.textContent = config.label;
    }
}

function stopVoiceActivityMonitor() {
    if (!state || !state.voice || !state.voice.activityMonitor) {
        setVoiceActivityIndicator('idle');
        return;
    }
    const monitor = state.voice.activityMonitor;
    if (monitor.rafId) {
        cancelAnimationFrame(monitor.rafId);
    }
    if (monitor.source) {
        try {
            monitor.source.disconnect();
        } catch (_) {}
    }
    if (monitor.context && typeof monitor.context.close === 'function') {
        monitor.context.close().catch(() => {});
    }
    state.voice.activityMonitor = null;
    setVoiceActivityIndicator('idle');
}

function startVoiceActivityMonitor(stream) {
    if (!stream) {
        return;
    }
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) {
        setVoiceActivityIndicator('unsupported');
        return;
    }
    stopVoiceActivityMonitor();

    const context = new AudioContextCtor();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);

    const dataArray = new Uint8Array(analyser.fftSize);
    const monitor = {
        context,
        analyser,
        source,
        dataArray,
        rafId: null,
        lastSpeechAt: performance.now(),
    };

    const threshold = 0.045;
    const silenceWindowMs = 600;

    const tick = () => {
        analyser.getByteTimeDomainData(dataArray);
        let sumSquares = 0;
        for (let i = 0; i < dataArray.length; i += 1) {
            const centered = (dataArray[i] - 128) / 128;
            sumSquares += centered * centered;
        }
        const rms = Math.sqrt(sumSquares / dataArray.length);
        const speaking = rms > threshold;
        if (speaking) {
            monitor.lastSpeechAt = performance.now();
            if (voiceActivityState !== 'speaking') {
                setVoiceActivityIndicator('speaking');
            }
        } else if (performance.now() - monitor.lastSpeechAt > silenceWindowMs) {
            if (voiceActivityState !== 'listening') {
                setVoiceActivityIndicator('listening');
            }
        }
        monitor.rafId = requestAnimationFrame(tick);
    };

    if (context.state === 'suspended' && typeof context.resume === 'function') {
        context.resume().catch(() => {});
    }

    state.voice.activityMonitor = monitor;
    setVoiceActivityIndicator('listening');
    tick();
}

function handleUserTranscriptChunk(transcript, options = {}) {
    if (!state || !state.voice) {
        return;
    }

    const finalize = !!options.finalize;
    const rawText = typeof transcript === 'string' ? transcript : '';
    const text = rawText.trim();
    const hasContent = text.length > 0;
    const questionIndex = state.currentQuestionIndex;

    if (!state.voice.userStream && !hasContent) {
        return;
    }

    if (!state.voice.userStream) {
        const meta = {
            ts: Date.now(),
            confidence: typeof options.confidence === 'number' ? options.confidence : undefined,
            source: options.source || undefined,
        };
        // If the previous finalized speaker was the user, continue appending to the
        // last 'You' bubble even for interim chunks to avoid creating a new bubble.
        const lastEntry = state.voice.messages && state.voice.messages[state.voice.messages.length - 1];
        // Prefer a purely structural check: if the last rendered entry is an existing
        // finalized 'You' bubble, continue appending text into it. This is resilient
        // to event ordering differences across browsers and realtime transports.
        // Structural coalescing: if the last rendered entry is a finalized
        // 'You' bubble, append text into it (covers both interim and final
        // chunks), until the Coach speaks.
        const mayContinueUserBubble = !!(lastEntry && lastEntry.role === 'user' && !lastEntry.stream && voiceTranscript && voiceTranscript.lastElementChild);
        if (mayContinueUserBubble) {
            const p = voiceTranscript.lastElementChild.querySelector('p');
            if (p) {
                const base = lastEntry.text || '';
                const joined = hasContent ? (base ? (base + ' ' + text) : text) : base;
                // Create a synthetic stream against the last entry
                state.voice.userStream = {
                    element: p,
                    entryIndex: state.voice.messages.length - 1,
                    text: joined,
                };
                p.textContent = joined;
                lastEntry.text = joined;
                lastEntry.stream = !finalize;
                if (Number.isInteger(questionIndex)) {
                    state.voice.transcriptsByIndex[questionIndex] = joined;
                }
                if (finalize && hasContent) {
                    const persistIdx = Number.isInteger(questionIndex) ? questionIndex : null;
                    persistVoiceMessage('user', text, { questionIndex: persistIdx });
                    state.voice.userStream = null;
                    state.voice.lastFinalSpeaker = 'user';
                }
                return;
            }
        }
        const result = appendVoiceMessage('user', text, { stream: !finalize, meta });
        if (!result) {
            return;
        }
        state.voice.userStream = {
            element: result.wrapper.querySelector('p'),
            entryIndex: result.entryIndex,
            text,
        };
    } else {
        const stream = state.voice.userStream;
        const updatedText = hasContent ? text : stream.text || '';
        stream.text = updatedText;
        if (stream.element) {
            stream.element.textContent = updatedText;
        }
        if (
            Number.isInteger(stream.entryIndex) &&
            state.voice.messages &&
            state.voice.messages[stream.entryIndex]
        ) {
            state.voice.messages[stream.entryIndex].text = updatedText;
            state.voice.messages[stream.entryIndex].stream = !finalize;
        }
    }

    const active = state.voice.userStream;

    if (!finalize && active && active.text) {
        if (Number.isInteger(questionIndex)) {
            state.voice.transcriptsByIndex[questionIndex] = active.text;
        }
        try { updateVoiceSubmitAvailability(); } catch (_) {}
        return;
    }

    if (finalize && active) {
        const finalText = (text || active.text || '').trim();
        if (!finalText) {
            state.voice.userStream = null;
            return;
        }

        // Deduplicate against the most recent finalized 'You' message (ignore case/punctuation)
        const normalize = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
        const currentNorm = normalize(finalText);
        try {
            for (let i = state.voice.messages.length - 1; i >= 0; i -= 1) {
                const m = state.voice.messages[i];
                if (m && m.role === 'user' && !m.stream && typeof m.text === 'string' && m.text.trim()) {
                    const lastNorm = normalize(m.text);
                    if (lastNorm === currentNorm) {
                        // Update index snapshot but skip duplicate append/persist
                        const qi = state.currentQuestionIndex;
                        if (Number.isInteger(qi)) {
                            state.voice.transcriptsByIndex[qi] = finalText;
                        }
                        state.voice.userStream = null;
                        return;
                    }
                    break;
                }
            }
        } catch (_) {}

        if (active.element) {
            active.element.textContent = finalText;
        }
        if (
            Number.isInteger(active.entryIndex) &&
            state.voice.messages &&
            state.voice.messages[active.entryIndex]
        ) {
            state.voice.messages[active.entryIndex].text = finalText;
            state.voice.messages[active.entryIndex].stream = false;
        }

        if (Number.isInteger(questionIndex)) {
            state.voice.transcriptsByIndex[questionIndex] = finalText;
        }

        if (answerInput) {
            const existingValue = answerInput.value || '';
            if (!existingValue.trim()) {
                answerInput.value = finalText;
            }
        }

        const persistIdx = Number.isInteger(questionIndex) ? questionIndex : null;
        persistVoiceMessage('user', finalText, { questionIndex: persistIdx });

        state.voice.userStream = null;
        state.voice.lastUserFinalNormalized = currentNorm;
        state.voice.lastFinalSpeaker = 'user';
        try { updateVoiceSubmitAvailability(); } catch (_) {}
    }
}

function persistVoiceMessage(role, message, options = {}) {
    if (!state.sessionId || !message) {
        return;
    }
    const trimmed = String(message).trim();
    if (!trimmed) {
        return;
    }
    const backendRole = voiceRoleToBackend[role] || role || 'system';
    const payload = {
        role: backendRole,
        text: trimmed,
        timestamp: options.timestamp || new Date().toISOString(),
        stream: !!options.stream,
    };
    if (Number.isInteger(options.questionIndex)) {
        payload.question_index = options.questionIndex;
    }
    fetch(`/session/${state.sessionId}/voice-messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    }).catch(() => {});
}

function appendVoiceMessage(role, message, options = {}) {
    if (!voiceTranscript || !message) {
        return null;
    }

    const text = message.trim();
    if (!text) {
        return null;
    }

    const qIndex = Number.isInteger(options.questionIndex)
        ? options.questionIndex
        : (Number.isInteger(state.currentQuestionIndex) ? state.currentQuestionIndex : null);
    const displayRole = voiceRoleToDisplay[role] || role;

    if (state && state.voice && Array.isArray(state.voice.messages) && !options.stream) {
        const existing = state.voice.messages[state.voice.messages.length - 1];
        if (existing && existing.role === displayRole && existing.text === text) {
            return null;
        }
    }

    if (voiceTranscript.dataset.empty === 'true') {
        voiceTranscript.innerHTML = '';
        delete voiceTranscript.dataset.empty;
    }

    const wrapper = document.createElement('div');

    if (displayRole === 'agent') {
        wrapper.className = 'bg-indigo-50 border border-indigo-100 text-indigo-800 text-sm rounded-lg p-3';
    } else if (displayRole === 'user') {
        wrapper.className = 'bg-white border border-gray-200 text-gray-800 text-sm rounded-lg p-3';
    } else {
        wrapper.className = 'text-xs text-gray-500';
    }

    if (displayRole === 'agent' || displayRole === 'user') {
        const label = document.createElement('div');
        label.className = 'text-xs uppercase tracking-wide font-semibold mb-1';
        label.textContent = displayRole === 'agent' ? 'Coach' : 'You';
        wrapper.appendChild(label);

            const content = document.createElement('p');
            content.textContent = text;
            wrapper.appendChild(content);
            if (state.voice && state.voice.config && state.voice.config.showMetadata && options.meta) {
            const meta = options.meta || {};
            const parts = [];
            if (meta.ts) {
                try {
                    const dt = new Date(meta.ts);
                    const hh = String(dt.getHours()).padStart(2, '0');
                    const mm = String(dt.getMinutes()).padStart(2, '0');
                    const ss = String(dt.getSeconds()).padStart(2, '0');
                    parts.push(`${hh}:${mm}:${ss}`);
                } catch (_) {}
            }
            if (typeof meta.confidence === 'number') {
                parts.push(`conf ${meta.confidence.toFixed(2)}`);
            }
            if (meta.source) {
                parts.push(String(meta.source));
            }
            if (parts.length) {
                const metaLine = document.createElement('div');
                metaLine.className = 'mt-1 text-[10px] text-gray-500';
                metaLine.textContent = parts.join(' • ');
                wrapper.appendChild(metaLine);
            }
        }
    } else {
        wrapper.textContent = text;
    }

    const entry = {
        role: displayRole,
        text,
        timestamp: new Date().toISOString(),
        stream: !!options.stream,
    };
    if (Number.isInteger(qIndex)) {
        entry.question_index = qIndex;
        if (state.questions && state.questions[qIndex]) {
            wrapper.title = state.questions[qIndex];
        }
    }
    if (options.meta) {
        entry.meta = options.meta;
    }
    let entryIndex = null;
    if (state && state.voice && Array.isArray(state.voice.messages)) {
        state.voice.messages.push(entry);
        entryIndex = state.voice.messages.length - 1;
    }

    // Attach question context tooltip
    if (Number.isInteger(qIndex) && state.questions && state.questions[qIndex]) {
        wrapper.title = state.questions[qIndex];
    }

    voiceTranscript.appendChild(wrapper);
    scrollVoiceTranscriptToBottom();

    return { wrapper, entry, entryIndex };
}

function appendAgentDelta(text) {
    if (!text) {
        return;
    }

    const cleanText = String(text).replace(/^\s+/g, '');
    if (!cleanText) {
        return;
    }

    if (!state.voice.agentStream || state.voice.agentStream.role !== 'agent') {
        const result = appendVoiceMessage('agent', cleanText, { stream: true });
        if (result) {
            const contentEl = result.wrapper.querySelector('p');
            state.voice.agentStream = {
                role: 'agent',
                element: contentEl,
                entryIndex: result.entryIndex,
                text: cleanText,
            };
        }
    } else {
        const stream = state.voice.agentStream;
        stream.text += cleanText;
        const updated = stream.text;
        if (stream.element) {
            stream.element.textContent = updated;
        }
        if (
            Array.isArray(state.voice.messages) &&
            state.voice.messages[stream.entryIndex]
        ) {
            state.voice.messages[stream.entryIndex].text = updated;
        }
    }
    state.voice.transcriptBuffer += cleanText;
}

function finalizeAgentMessage() {
    const active = state.voice.agentStream;
    const finalText = (active && active.text ? active.text : state.voice.transcriptBuffer).trim();

    if (active && active.element) {
        // Format coach text (STAR + I) into readable lines within the bubble
        const html = renderCoachTranscriptHtml(finalText);
        if (html) {
            active.element.innerHTML = html;
        } else {
            active.element.textContent = finalText;
        }
    }
    if (
        active &&
        Array.isArray(state.voice.messages) &&
        state.voice.messages[active.entryIndex]
    ) {
        state.voice.messages[active.entryIndex].text = finalText;
        state.voice.messages[active.entryIndex].stream = false;
    }
    if (!active && finalText) {
        const result = appendVoiceMessage('agent', finalText);
        if (
            result &&
            Array.isArray(state.voice.messages) &&
            state.voice.messages[result.entryIndex]
        ) {
            state.voice.messages[result.entryIndex].stream = false;
        }
    }

    if (finalText) {
        const idx = state.currentQuestionIndex;
        const persistIdx = Number.isInteger(idx) ? idx : null;
        persistVoiceMessage('agent', finalText, { questionIndex: persistIdx });
    }

    state.voice.agentStream = null;
    state.voice.transcriptBuffer = '';
    if (state.voice) { state.voice.lastFinalSpeaker = 'agent'; }
    try { updateVoiceSubmitAvailability(); } catch (_) {}
}

function handleVoiceEvent(event) {
    if (!event || !event.type) {
        return;
    }

    switch (event.type) {
        case 'response.output_text.delta': {
            const delta = event.delta || event.text || '';
            appendAgentDelta(delta);
            break;
        }
        case 'response.delta': {
            const outputs = event.delta?.output || event.delta?.outputs || [];
            if (Array.isArray(outputs)) {
                outputs.forEach((item) => {
                    if (!item) return;
                    const type = item.type || item.kind || '';
                    if (type === 'output_text.delta') {
                        const text = item.text || item.content || item.content?.text || '';
                        appendAgentDelta(text);
                    } else if (type === 'output_text.done') {
                        finalizeAgentMessage();
                    } else if (type === 'output_audio_buffer' && Array.isArray(item.parts)) {
                        item.parts.forEach((part) => {
                            if (part && typeof part.transcript === 'string' && part.transcript.trim()) {
                                appendAgentDelta(part.transcript);
                                finalizeAgentMessage();
                            }
                        });
                    }
                });
            }
            break;
        }
        case 'response.content_part.added': {
            const part = event.part || {};
            if (part.type === 'audio' && typeof part.transcript === 'string') {
                appendAgentDelta(part.transcript);
            }
            break;
        }
        case 'response.content_part.done': {
            const part = event.part || {};
            if (part.type === 'audio' && typeof part.transcript === 'string') {
                appendAgentDelta(part.transcript);
                finalizeAgentMessage();
                // Agent finished a spoken segment; allow browser ASR again
                if (state.voice) {
                    state.voice.agentSpeaking = false;
                    state.voice.suppressBrowserAsr = false;
                }
            }
            break;
        }
        case 'output_audio_buffer.started': {
            state.voice.transcriptBuffer = '';
            state.voice.agentStream = null;
            if (state.voice) {
                state.voice.agentSpeaking = true;
                state.voice.suppressBrowserAsr = true;
            }
            break;
        }
        case 'response.output_text.done':
        case 'response.completed': {
            finalizeAgentMessage();
            if (state.voice) {
                state.voice.agentSpeaking = false;
                state.voice.suppressBrowserAsr = false;
            }
            break;
        }
        case 'response.created': {
            if (!state.voice.agentStream) {
                appendAgentDelta('');
            }
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
        case 'response.input_audio_transcription.completed':
        case 'input_audio_buffer.speech_transcribed': {
            const transcriptText = event.transcript || event.text || '';
            handleUserTranscriptChunk(transcriptText, { finalize: true });
            break;
        }
        case 'conversation.item.input_audio_transcription.delta':
        case 'response.input_audio_transcription.delta':
        case 'input_audio_buffer.transcript.delta': {
            const deltaText =
                event.delta?.transcript ||
                event.transcript ||
                (Array.isArray(event.deltas) ? event.deltas.map((d) => d.transcript).join(' ') : '');
            handleUserTranscriptChunk(deltaText);
            break;
        }
        case 'input_audio_buffer.speech_started': {
            setVoiceActivityIndicator('speaking');
            break;
        }
        case 'input_audio_buffer.speech_stopped':
        case 'input_audio_buffer.committed': {
            setVoiceActivityIndicator('listening');
            break;
        }
        case 'conversation.item.created':
        case 'conversation.item.updated': {
            const item = event.item || {};
            const role = (item.role || '').toLowerCase();
            let text = extractTranscriptFromRealtimeItem(item);
            const isFinal = item.status === 'completed' || event.type === 'conversation.item.updated';
            const contentParts = Array.isArray(item.content) ? item.content : [];
            const hasAudioOnly =
                contentParts.length > 0 &&
                contentParts.every(
                    (part) =>
                        part &&
                        typeof part === 'object' &&
                        (part.type === 'input_audio' || part.type === 'audio' || part.type === 'audio_attachment')
                );
            const hasTextLikePart = contentParts.some(
                (part) =>
                    part &&
                    typeof part === 'object' &&
                    ['input_text', 'output_text', 'text', 'input_audio.transcription'].includes(part.type) &&
                    typeof (part.text || part.transcript || part.value) === 'string'
            );

            if (hasAudioOnly && !hasTextLikePart) {
                text = '';
            }

            if ((role === 'user' || role === 'candidate') && text) {
                if (/^input_audio$/i.test(text)) {
                    text = '';
                }
            }

            if ((role === 'user' || role === 'candidate') && text) {
                handleUserTranscriptChunk(text, { finalize: isFinal });
            } else if ((role === 'assistant' || role === 'coach') && text && isFinal) {
                // Avoid duplicating existing streaming updates
                if (!state.voice.agentStream) {
                    const res = appendVoiceMessage('agent', text, { stream: false });
                    // Apply formatting to the newly created agent bubble
                    try {
                        const el = res && res.wrapper && res.wrapper.querySelector('p');
                        if (el) {
                            const html = renderCoachTranscriptHtml(text);
                            if (html) el.innerHTML = html;
                        }
                    } catch (_) {}
                    const idx = state.currentQuestionIndex;
                    const persistIdx = Number.isInteger(idx) ? idx : null;
                    persistVoiceMessage('agent', text, { questionIndex: persistIdx });
                    if (state.voice) { state.voice.lastFinalSpeaker = 'agent'; }
                }
            }
            break;
        }
        default: {
            if (event && typeof event === 'object') {
                const rawType = typeof event.type === 'string' ? event.type.toLowerCase() : '';
                const roleCandidates = [
                    event.role,
                    event.source && event.source.role,
                    event.participant && event.participant.role,
                    event.delta && event.delta.role,
                    event.delta && event.delta.source && event.delta.source.role,
                ]
                    .filter(Boolean)
                    .map((role) => String(role).toLowerCase());

                const fromUserRole = roleCandidates.some((role) => role === 'user' || role === 'candidate');
                const looksLikeUserInput =
                    rawType.includes('input_audio') ||
                    rawType.includes('speech') ||
                    rawType.includes('microphone');

                if (fromUserRole || looksLikeUserInput) {
                    const fallbackTranscript =
                        event.transcript ||
                        (event.delta && event.delta.transcript) ||
                        (Array.isArray(event.deltas) ? event.deltas.map((d) => d.transcript).join(' ') : '');
                    if (fallbackTranscript) {
                        handleUserTranscriptChunk(fallbackTranscript, { finalize: true });
                        break;
                    }
                }
            }
            if (event.type && event.type.startsWith('response.audio')) {
                return;
            }
            if (event.type !== 'response.created' && event.type !== 'response.output_text.created') {
                console.debug('Voice event:', event);
            }
        }
    }
}

// Build simple HTML for coach transcript lines using STAR + I cues
function renderCoachTranscriptHtml(text) {
    if (!text) return '';
    let t = String(text).trim();
    // Trim generic preface up to first STAR+I label if present
    try {
        const firstIdx = t.search(/\b(Situation|Task|Action|Result|Impact)\s*:/i);
        if (firstIdx > 0) t = t.slice(firstIdx);
    } catch (_) {}
    // Escape HTML then inject bold labels with line breaks
    let html = escapeHtml(t);
    html = html.replace(/\b(Situation|Task|Action|Result|Impact)\s*:/gi, function(_, label){
        return (html.startsWith('<strong>') ? '' : '<br>') + '<strong>' + label.charAt(0).toUpperCase() + label.slice(1).toLowerCase() + ':</strong>';
    });
    // Ensure no leading <br>
    html = html.replace(/^<br>/, '');
    return html;
}

function hydrateVoiceMessagesFromSession(sessionData) {
    if (!sessionData) {
        return;
    }
    if (!state.voice) {
        state.voice = createInitialVoiceState();
    }
    clearVoiceTranscript();

    const transcripts = sessionData.voice_transcripts || {};
    state.voice.transcriptsByIndex = {};
    Object.entries(transcripts).forEach(([key, value]) => {
        const numericKey = Number.isNaN(Number(key)) ? key : Number(key);
        state.voice.transcriptsByIndex[numericKey] = value;
    });

    const messages = Array.isArray(sessionData.voice_messages) ? sessionData.voice_messages : [];
    messages.forEach((msg) => {
        if (!msg || !msg.text) {
            return;
        }
        const role = (msg.role || 'system');
        const displayRole = voiceRoleToDisplay[role] || role;
        const last = state.voice.messages && state.voice.messages[state.voice.messages.length - 1];
        if (displayRole === 'user' && last && last.role === 'user' && !msg.stream) {
            const wrapper = voiceTranscript && voiceTranscript.lastElementChild;
            if (wrapper) {
                const p = wrapper.querySelector('p');
                if (p) {
                    const joined = (last.text ? (last.text + ' ' + msg.text) : msg.text).trim();
                    p.textContent = joined;
                    last.text = joined;
                    return;
                }
            }
        }
        const result = appendVoiceMessage(role, msg.text, { stream: !!msg.stream });
        if (result && state.voice.messages[result.entryIndex]) {
            if (msg.timestamp) {
                state.voice.messages[result.entryIndex].timestamp = msg.timestamp;
            }
            if (typeof msg.question_index === 'number') {
                state.voice.messages[result.entryIndex].question_index = msg.question_index;
            }
            // Apply STAR+I formatting to hydrated Coach bubbles for consistency
            try {
                if (role === 'coach' || role === 'agent') {
                    const p = result.wrapper && result.wrapper.querySelector('p');
                    if (p) {
                        const html = renderCoachTranscriptHtml(msg.text);
                        if (html) p.innerHTML = html;
                    }
                }
            } catch (_) { /* formatting is best-effort */ }
        }
    });
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
    setVoiceLayout(true);
    updateVoiceStatus('Connecting...', 'pending');
    const hasHistory = state.voice && Array.isArray(state.voice.messages) && state.voice.messages.length > 0;
    if (hasHistory) {
        appendVoiceMessage('system', '--- Starting new voice session ---');
    } else {
        clearVoiceTranscript();
        appendVoiceMessage('system', '--- Starting voice session ---');
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
            // Only start browser ASR if explicitly enabled and not suppressed
            if (
                state.voice &&
                state.voice.config &&
                state.voice.config.useBrowserAsr &&
                !state.voice.suppressBrowserAsr
            ) {
                startBrowserAsrIfAvailable();
            }
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
        startVoiceActivityMonitor(localStream);

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
        if (error && (error.name === 'NotAllowedError' || error.name === 'SecurityError')) {
            setVoiceActivityIndicator('muted');
        } else if (error && (error.name === 'NotFoundError' || error.name === 'NotReadableError')) {
            setVoiceActivityIndicator('unsupported');
        }
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

    stopVoiceActivityMonitor();
    stopBrowserAsr();
    state.voice = createInitialVoiceState();

    if (!preserveStatus) {
        updateVoiceStatus(silent ? 'Offline' : 'Voice session ended', 'idle');
    }

    setVoiceControls(false);
    setVoiceLayout(false);
    try { updateVoiceSubmitAvailability(); } catch (_) {}
}

function updateVoiceSubmitAvailability() {
    if (!submitVoiceBtn || !state || !state.voice) return;
    const idx = state.currentQuestionIndex;
    const t = Number.isInteger(idx) && state.voice.transcriptsByIndex
        ? (state.voice.transcriptsByIndex[idx] || '')
        : '';
    const ready = typeof t === 'string' && t.trim().length >= 10; // minimal threshold
    submitVoiceBtn.disabled = !ready;
    submitVoiceBtn.classList.toggle('opacity-50', !ready);
    submitVoiceBtn.classList.toggle('cursor-not-allowed', !ready);
}

async function handleVoiceAnswerSubmission() {
    if (!state || !state.sessionId) {
        alert('Start or resume a session first.');
        return;
    }
    const idx = state.currentQuestionIndex;
    const question = state.questions[idx];
    const transcript = (state.voice && state.voice.transcriptsByIndex && Number.isInteger(idx))
        ? (state.voice.transcriptsByIndex[idx] || '').trim()
        : '';
    if (!transcript) {
        alert('No voice transcript available yet. Speak your answer, then submit.');
        return;
    }
    if (state.isRecording) {
        try { stopRecording(); } catch (_) {}
    }
    const orig = submitVoiceBtn ? submitVoiceBtn.textContent : '';
    if (submitVoiceBtn) { submitVoiceBtn.disabled = true; submitVoiceBtn.textContent = 'Submitting…'; }
    try {
        const res = await fetch('/evaluate-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                question,
                answer: transcript,
                voice_transcript: transcript,
            })
        });
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(errText || 'Failed to submit voice answer');
        }
        const data = await res.json();
        const evaluation = data && data.evaluation ? data.evaluation : null;
        if (evaluation) {
            state.answers.push({ question, answer: transcript });
            state.evaluations.push(evaluation);
            displayFeedback(evaluation);
        } else {
            alert('No evaluation returned.');
        }
    } catch (err) {
        console.error('Voice submit error:', err);
        alert('Unable to submit voice answer.');
    } finally {
        if (submitVoiceBtn) { submitVoiceBtn.textContent = orig; }
        updateVoiceSubmitAvailability();
    }
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
    
    // Handle recognition results (browser ASR fallback)
    state.recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        let finalConfidence = null;
        
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
                if (typeof event.results[i][0].confidence === 'number') {
                    finalConfidence = event.results[i][0].confidence;
                }
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        
        if (finalTranscript) {
            // Append to textarea instead of replacing
            answerInput.value += ' ' + finalTranscript;
            if (state.voice && state.voice.config && state.voice.config.useBrowserAsr && !state.voice.suppressBrowserAsr) {
                try { handleUserTranscriptChunk(finalTranscript, { finalize: true, source: 'browser_asr', confidence: finalConfidence }); } catch (_) {}
            }
        } else if (interimTranscript) {
            if (state.voice && state.voice.config && state.voice.config.useBrowserAsr && !state.voice.suppressBrowserAsr) {
                try { handleUserTranscriptChunk(interimTranscript, { finalize: false, source: 'browser_asr' }); } catch (_) {}
            }
        }
    };
    
    state.recognition.onspeechstart = () => {
        setVoiceActivityIndicator('speaking');
    };
    state.recognition.onspeechend = () => {
        setVoiceActivityIndicator('listening');
    };
    
    state.recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        stopBrowserAsr();
    };
    
    state.recognition.onend = () => {
        state.isRecording = false;
        state.voice.browserAsrActive = false;
        // When voice session is live, attempt to restart for continuous capture
        if (state.voice && state.voice.peer && state.voice.dataChannel && state.voice.config && state.voice.config.useBrowserAsr && !state.voice.suppressBrowserAsr) {
            try { state.recognition.start(); state.isRecording = true; state.voice.browserAsrActive = true; } catch (_) {}
        }
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
            if (state.voice) { state.voice.browserAsrActive = true; }
            
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
        if (state.voice) { state.voice.browserAsrActive = false; }
        
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

function startBrowserAsrIfAvailable() {
    try {
        if (!state.recognition) {
            if (!setupSpeechRecognition()) return;
        }
        state.recognition.start();
        state.isRecording = true;
        if (state.voice) { state.voice.browserAsrActive = true; }
    } catch (e) {
        // Some browsers require a user gesture; ignore failures
    }
}

function stopBrowserAsr() {
    try {
        if (state.recognition) {
            state.recognition.stop();
        }
    } catch (_) {}
    state.isRecording = false;
    if (state.voice) { state.voice.browserAsrActive = false; }
}

// Event listeners
    document.addEventListener('DOMContentLoaded', () => {
        setupEventListeners();
        setupSpeechRecognition();
        clearVoiceTranscript();
        updateVoiceStatus('Offline', 'idle');
        setVoiceControls(false);
        setVoiceEnabled(false);
        if (voiceTranscript) voiceTranscript.dataset.freeze = 'false';
        refreshSessionsList(state.sessionId);
            refreshSwitcherList();
        initVoiceSelector();
        // Initialize coach level select/save (loads current level on active session)
        (async () => { try { await initCoachLevelSelector(); } catch (_) {} })();
    // Initialize voice settings toggles
    if (toggleBrowserAsr) {
        toggleBrowserAsr.checked = !!(state.voice && state.voice.config && state.voice.config.useBrowserAsr);
        toggleBrowserAsr.addEventListener('change', () => {
            if (state.voice && state.voice.config) {
                state.voice.config.useBrowserAsr = !!toggleBrowserAsr.checked;
                if (!toggleBrowserAsr.checked) {
                    stopBrowserAsr();
                } else if (state.voice.peer && state.voice.dataChannel) {
                    startBrowserAsrIfAvailable();
                }
            }
        });
    }
        if (toggleShowMetadata) {
            toggleShowMetadata.checked = !!(state.voice && state.voice.config && state.voice.config.showMetadata);
            toggleShowMetadata.addEventListener('change', () => {
                if (state.voice && state.voice.config) {
                    state.voice.config.showMetadata = !!toggleShowMetadata.checked;
                }
            });
        }
        if (voiceTranscriptFreeze && voiceTranscript) {
            voiceTranscriptFreeze.checked = voiceTranscript.dataset.freeze === 'true';
            voiceTranscriptFreeze.addEventListener('change', () => {
                voiceTranscript.dataset.freeze = voiceTranscriptFreeze.checked ? 'true' : 'false';
                if (!voiceTranscriptFreeze.checked) scrollVoiceTranscriptToBottom();
            });
        }
    if (exportTranscriptBtn) {
        exportTranscriptBtn.addEventListener('click', exportFullTranscript);
    }
    if (submitVoiceBtn) {
        submitVoiceBtn.addEventListener('click', handleVoiceAnswerSubmission);
        try { updateVoiceSubmitAvailability(); } catch (_) {}
    }
    if (muteVoiceBtn) {
        muteVoiceBtn.addEventListener('click', toggleMuteVoice);
    }
    if (newInterviewBtn) {
        newInterviewBtn.addEventListener('click', startNewInterviewFlow);
    }
    if (openSessionsBtn && sessionsModal) {
        openSessionsBtn.addEventListener('click', async () => {
            await refreshSessionsModalList('');
            sessionsModal.classList.remove('hidden');
        });
    }
    if (openSettingsBtn && voiceSettingsDrawer) {
        openSettingsBtn.addEventListener('click', async () => {
            await populateVoiceSettingsDrawer();
            voiceSettingsDrawer.classList.remove('hidden');
        });
    }
    if (sessionsCloseBtn && sessionsModal) {
        sessionsCloseBtn.addEventListener('click', () => sessionsModal.classList.add('hidden'));
    }
    if (sessionsRefresh) {
        sessionsRefresh.addEventListener('click', async () => refreshSessionsModalList(sessionsSearch && sessionsSearch.value || ''));
    }
    if (sessionsSearch) {
        sessionsSearch.addEventListener('input', async () => refreshSessionsModalList(sessionsSearch.value || ''));
    }
    if (sessionsLoadBtn) {
        sessionsLoadBtn.addEventListener('click', async () => {
            const id = sessionsModalSelect && sessionsModalSelect.value;
            if (!id) return;
            sessionsModal.classList.add('hidden');
            await resumeSavedSessionById(id);
        });
    }
    if (sessionsRenameBtn) {
        sessionsRenameBtn.addEventListener('click', async () => {
            const id = sessionsModalSelect && sessionsModalSelect.value;
            const name = sessionsRenameInput && sessionsRenameInput.value.trim();
            if (!id || !name) return alert('Select a session and enter a new name.');
            try {
                const r = await fetch(`/session/${id}/name`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
                if (!r.ok) throw new Error(await r.text());
                sessionsRenameInput.value = '';
                await refreshSessionsModalList(sessionsSearch && sessionsSearch.value || '');
            } catch (err) { alert(err.message || 'Unable to rename'); }
        });
    }
    if (sessionsDeleteBtn) {
        sessionsDeleteBtn.addEventListener('click', async () => {
            const id = sessionsModalSelect && sessionsModalSelect.value;
            if (!id) return;
            if (!confirm('Delete this session permanently?')) return;
            try {
                const r = await fetch(`/session/${id}`, { method: 'DELETE' });
                if (!r.ok && r.status !== 404) throw new Error(await r.text());
                await refreshSessionsModalList(sessionsSearch && sessionsSearch.value || '');
                await refreshSessionsList();
                await refreshSwitcherList();
            } catch (err) { alert(err.message || 'Unable to delete'); }
        });
    }
    if (openQuestionDrawerBtn && questionDrawer) {
        openQuestionDrawerBtn.addEventListener('click', () => {
            buildQuestionRail();
            questionDrawer.classList.remove('hidden');
        });
    }
    if (closeQuestionDrawerBtn && questionDrawer) {
        closeQuestionDrawerBtn.addEventListener('click', () => questionDrawer.classList.add('hidden'));
    }
    if (prevQuestionBtn) prevQuestionBtn.addEventListener('click', () => { if (state.currentQuestionIndex > 0) displayQuestion(state.currentQuestionIndex - 1); });
    if (nextQuestionFooterBtn) nextQuestionFooterBtn.addEventListener('click', handleNextQuestion);
    if (markReviewBtn) markReviewBtn.addEventListener('click', toggleMarkForReview);
    if (openVoiceSettingsBtn && voiceSettingsDrawer) {
        openVoiceSettingsBtn.addEventListener('click', async () => {
            await populateVoiceSettingsDrawer();
            voiceSettingsDrawer.classList.remove('hidden');
        });
    }
    if (closeVoiceSettingsBtn && voiceSettingsDrawer) {
        closeVoiceSettingsBtn.addEventListener('click', () => voiceSettingsDrawer.classList.add('hidden'));
    }
    // Drawer: preview and save
    if (voicePreviewBtn2 && voiceSelect2 && voicePreviewAudio2) {
        voicePreviewBtn2.addEventListener('click', async () => {
            await populateVoiceSettingsDrawer();
            const opt = voiceSelect2.options[voiceSelect2.selectedIndex];
            let url = opt && opt.dataset.previewUrl;
            if (!url && opt && opt.value) url = `/voices/preview/${encodeURIComponent(opt.value)}`;
            if (!url) return alert('No preview available for this voice.');
            try {
                voicePreviewAudio2.src = url;
                voicePreviewAudio2.classList.remove('hidden');
                await voicePreviewAudio2.play().catch(() => {});
            } catch (_) {}
        });
    }
    if (voiceSaveBtn2 && voiceSelect2) {
        voiceSaveBtn2.addEventListener('click', async () => {
            if (!state.sessionId) return alert('Start or resume a session first.');
            const voiceId = voiceSelect2.value;
            try {
                const r = await fetch(`/session/${state.sessionId}/voice`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ voice_id: voiceId }) });
                if (!r.ok) throw new Error(await r.text());
                if (voiceSelect) voiceSelect.value = voiceId;
                // Offer to apply immediately by restarting the voice session
                let applied = false;
                if (state.voice && state.voice.peer) {
                    applied = confirm('Voice saved. Restart the voice session now to apply the new voice?');
                    if (applied) {
                        try { stopVoiceInterview({ silent: true }); } catch (_) {}
                        setTimeout(() => startVoiceInterview(), 150);
                    }
                }
                if (!applied) alert('Voice saved. New prompts will use this voice.');
            } catch (err) {
                alert(err.message || 'Unable to save voice');
            }
        });
    }
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

    if (renameSessionBtn) {
        renameSessionBtn.addEventListener('click', async (event) => {
            event.preventDefault();
            await renameSelectedSession();
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

    bindCustomQuestionControls();

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

    if (switchSessionBtn) {
        switchSessionBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const id = switchSessionsSelect && switchSessionsSelect.value;
            if (!id) return;
            await resumeSavedSessionById(id);
        });
    }

    if (viewDocsBtn) {
        viewDocsBtn.addEventListener('click', toggleDocsPanel);
    }
}

async function initVoiceSelector() {
    try {
        const voices = await ensureVoicesCatalog();
        if (voiceSelect) {
            while (voiceSelect.firstChild) voiceSelect.removeChild(voiceSelect.firstChild);
            voices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.label || v.id;
                if (v.preview_url) opt.dataset.previewUrl = v.preview_url;
                voiceSelect.appendChild(opt);
            });
        }
        if (voicePreviewBtn && voiceSelect && voicePreviewAudio) {
            const setPreviewLoading = (loading) => {
                const orig = voicePreviewBtn.dataset.origLabel || voicePreviewBtn.textContent;
                if (!voicePreviewBtn.dataset.origLabel) {
                    voicePreviewBtn.dataset.origLabel = orig;
                }
                voicePreviewBtn.disabled = !!loading;
                voicePreviewBtn.classList.toggle('opacity-50', !!loading);
                voiceSelect.disabled = !!loading;
                if (startVoiceBtn) startVoiceBtn.disabled = !!loading;
                voicePreviewBtn.textContent = loading ? 'Loading…' : voicePreviewBtn.dataset.origLabel;
            };

            // Ensure UI is restored when preview finishes or errors
            const attachAutoRestore = () => {
                const restore = () => setPreviewLoading(false);
                voicePreviewAudio.addEventListener('playing', restore, { once: true });
                voicePreviewAudio.addEventListener('canplay', restore, { once: true });
                voicePreviewAudio.addEventListener('error', restore, { once: true });
                voicePreviewAudio.addEventListener('ended', restore, { once: true });
            };

            voicePreviewBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                const opt = voiceSelect.options[voiceSelect.selectedIndex];
                let url = opt && opt.dataset.previewUrl;
                if (!url && opt && opt.value) url = `/voices/preview/${encodeURIComponent(opt.value)}`; // fallback
                if (!url) {
                    alert('No preview available for this voice.');
                    return;
                }
                try {
                    // UI loading state
                    setPreviewLoading(true);
                    attachAutoRestore();
                    // Stop any current preview
                    try { voicePreviewAudio.pause(); } catch (_) {}
                    voicePreviewAudio.currentTime = 0;
                    // Start new preview
                    voicePreviewAudio.src = url;
                    voicePreviewAudio.classList.remove('hidden');
                    await voicePreviewAudio.play().catch(() => {});
                } catch (_) {
                    setPreviewLoading(false);
                }
            });
        }
        if (voiceSaveBtn && voiceSelect) {
            voiceSaveBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                if (!state.sessionId) {
                    alert('Start or resume a session first.');
                    return;
                }
                const voiceId = voiceSelect.value;
                if (!voiceId) return;
                try {
                    const r = await fetch(`/session/${state.sessionId}/voice`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ voice_id: voiceId })
                    });
                    if (!r.ok) {
                        const detail = await r.text();
                        throw new Error(detail || 'Failed to save voice');
                    }
                    // Mirror selection into the drawer select if present
                    if (voiceSelect2) {
                        voiceSelect2.value = voiceId;
                    }
                    // Offer to apply immediately by restarting the voice session
                    let applied = false;
                    if (state.voice && state.voice.peer) {
                        applied = confirm('Voice saved. Restart the voice session now to apply the new voice?');
                        if (applied) {
                            try { stopVoiceInterview({ silent: true }); } catch (_) {}
                            setTimeout(() => startVoiceInterview(), 150);
                        }
                    }
                    if (!applied) alert('Voice saved. New prompts will use this voice.');
                } catch (err) {
                    alert(err.message || 'Unable to save voice');
                }
            });
        }
    } catch (err) {
        console.warn('Voice catalog unavailable:', err);
    }
}

// Shared voices loader with cache + retry
let __voicesCache = null;
let __voicesPromise = null;
async function ensureVoicesCatalog(force = false) {
    if (!force && __voicesCache && Array.isArray(__voicesCache) && __voicesCache.length > 0) {
        return __voicesCache;
    }
    if (!force && __voicesPromise) return __voicesPromise;
    __voicesPromise = (async () => {
        const res = await fetch('/voices');
        if (!res.ok) throw new Error('Failed to load voices');
        const list = await res.json();
        __voicesCache = Array.isArray(list) ? list : [];
        return __voicesCache;
    })().finally(() => {
        __voicesPromise = null;
    });
    return __voicesPromise;
}

async function loadSessionDocuments(sessionId) {
    if (!sessionId) return;
    try {
        const res = await fetch(`/session/${sessionId}/documents`);
        if (!res.ok) throw new Error('Failed to load documents');
        const data = await res.json();
        state.resumeText = (data && data.resume_text) || '';
        state.jobDescText = (data && data.job_desc_text) || '';
        if (docsPanel && !docsPanel.classList.contains('hidden')) {
            if (resumeDocEl) resumeDocEl.textContent = state.resumeText || '';
            if (jobDocEl) jobDocEl.textContent = state.jobDescText || '';
        }
    } catch (err) {
        console.error('Docs load error:', err);
        throw err;
    }
}

function syncVoiceSettingsSummary() {
    const voiceId = state && state.voice && state.voice.selectedVoiceId;
    if (voiceId) {
        if (voiceSelect) voiceSelect.value = voiceId;
        if (voiceSelect2) voiceSelect2.value = voiceId;
    }
    const cfg = state && state.voice && state.voice.config;
    if (cfg) {
        if (toggleBrowserAsr) toggleBrowserAsr.checked = !!cfg.useBrowserAsr;
        if (toggleShowMetadata) toggleShowMetadata.checked = !!cfg.showMetadata;
        if (toggleBrowserAsr2) toggleBrowserAsr2.checked = !!cfg.useBrowserAsr;
        if (toggleShowMetadata2) toggleShowMetadata2.checked = !!cfg.showMetadata;
    }
}

async function initCoachLevelSelector() {
    if (!coachLevelSelect) return;
    try {
        if (state.sessionId) {
            const r = await fetch(`/session/${state.sessionId}`);
            if (r.ok) {
                const data = await r.json();
                const lvl = (data && data.coach_level) || 'level_1';
                coachLevelSelect.value = lvl;
            }
        }
    } catch (_) {}

    if (coachLevelSaveBtn) {
        coachLevelSaveBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!state.sessionId) {
                alert('Start or resume a session first.');
                return;
            }
            const lvl = coachLevelSelect.value || 'level_1';
            try {
                const r = await fetch(`/session/${state.sessionId}/coach-level`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ level: lvl })
                });
                if (!r.ok) {
                    const t = await r.text();
                    throw new Error(t || 'Failed to save level');
                }
                alert('Coaching level saved. New prompts will use this level.');
            } catch (err) {
                alert(err.message || 'Unable to save level');
            }
        });
    }
}

function exportFullTranscript() {
    if (!state.sessionId) {
        alert('Start a session first.');
        return;
    }
    fetch(`/session/${state.sessionId}`)
        .then(r => (r.ok ? r.json() : Promise.reject(new Error('Failed to load session'))))
        .then(data => {
            // Base conversation from persisted voice_messages
            const msgs = Array.isArray(data.voice_messages) ? data.voice_messages.slice() : [];

            // Some users report exports missing 'You' lines when only the
            // per-question transcript (voice_transcripts) was captured. As a
            // safety net, inject a synthetic 'You' entry for any question index
            // that has a transcript but no candidate message persisted.
            try {
                const transcripts = (data && data.voice_transcripts) || {};
                const hasCandidateByIdx = new Set(
                    msgs
                        .filter(m => m && (m.role === 'candidate' || m.role === 'user') && typeof m.question_index === 'number')
                        .map(m => m.question_index)
                );
                Object.keys(transcripts).forEach(k => {
                    const idx = Number(k);
                    const text = (transcripts[k] || '').trim();
                    if (!text) return;
                    if (!hasCandidateByIdx.has(idx)) {
                        msgs.push({ role: 'candidate', text, question_index: idx, timestamp: '' });
                    }
                });
            } catch (_) { /* ignore fallback wiring issues */ }

            // Sort messages: by timestamp when both present; otherwise by
            // question_index and role order (You -> Coach -> System), stable by original order.
            const roleRank = (m) => {
                const r = (m.role || '').toLowerCase();
                if (r === 'candidate' || r === 'user') return 0; // You
                if (r === 'coach' || r === 'agent' || r === 'assistant') return 1; // Coach
                if (r === 'system') return 2;
                return 3;
            };
            const withIndex = msgs.map((m, i) => ({ ...m, _i: i }));
            const hasTs = (m) => {
                if (!m || !m.timestamp) return false;
                const t = Date.parse(m.timestamp);
                return !Number.isNaN(t);
            };
            withIndex.sort((a, b) => {
                const aHas = hasTs(a);
                const bHas = hasTs(b);
                if (aHas && bHas) {
                    return Date.parse(a.timestamp) - Date.parse(b.timestamp);
                }
                const qa = Number.isInteger(a.question_index) ? a.question_index : Number.POSITIVE_INFINITY;
                const qb = Number.isInteger(b.question_index) ? b.question_index : Number.POSITIVE_INFINITY;
                if (qa !== qb) return qa - qb;
                const ra = roleRank(a);
                const rb = roleRank(b);
                if (ra !== rb) return ra - rb;
                return a._i - b._i;
            });

            // Coalesce consecutive 'You' lines to mirror UI behavior
            const coalesced = [];
            for (const m of withIndex) {
                const role = (m.role === 'coach' || m.role === 'agent') ? 'Coach' : (m.role === 'candidate' || m.role === 'user') ? 'You' : 'System';
                if (coalesced.length > 0 && role === 'You' && coalesced[coalesced.length - 1].role === 'You') {
                    // Merge text, preserve earliest timestamp
                    const prev = coalesced[coalesced.length - 1];
                    const joined = [prev.text, m.text].filter(Boolean).join(' ').trim();
                    prev.text = joined;
                    // Keep prev.timestamp as-is (earliest)
                    continue;
                }
                coalesced.push({
                    role,
                    text: m.text || '',
                    timestamp: m.timestamp || '',
                });
            }

            // Format a simple, readable text export
            const lines = [];
            coalesced.forEach(m => {
                const ts = m.timestamp ? new Date(m.timestamp).toISOString() : '';
                const line = [ts, m.role + ':', m.text || ''].filter(Boolean).join(' ');
                lines.push(line);
            });
            const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `interview_transcript_${(state.sessionName || state.sessionId || 'session')}.txt`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(a.href), 1000);
        })
        .catch(() => alert('Unable to export transcript.'));
}

async function renameSelectedSession() {
    const selectedId = sessionsSelect && sessionsSelect.value ? sessionsSelect.value : null;
    if (!selectedId) {
        alert('Select a session to rename.');
        return;
    }
    const newName = (renameSessionInput && renameSessionInput.value || '').trim();
    if (!newName) {
        alert('Enter a new name for the session.');
        return;
    }
    try {
        const res = await fetch(`/session/${selectedId}/name`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        if (!res.ok) {
            const detail = await res.text();
            throw new Error(detail || 'Failed to rename session');
        }
        renameSessionInput.value = '';
        await refreshSessionsList(selectedId);
        await refreshSwitcherList();
    } catch (err) {
        console.error('Error renaming session:', err);
        alert('Unable to rename session.');
    }
}

async function refreshSessionsList(preselectId = null) {
    if (!resumeActions || !sessionsSelect) {
        return;
    }
    try {
        const res = await fetch('/sessions');
        if (!res.ok) {
            throw new Error('Failed to load sessions');
        }
        const items = await res.json();
        sessionsSelect.innerHTML = '';
        if (Array.isArray(items) && items.length > 0) {
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = `${item.name || 'Session'}${item.questions_count ? ` • ${item.questions_count} q` : ''}`;
                sessionsSelect.appendChild(opt);
            });
            const last = preselectId || localStorage.getItem('interviewSessionId');
            if (last) {
                sessionsSelect.value = last;
            }
            resumeActions.classList.remove('hidden');
            if (sessionsCount) {
                sessionsCount.textContent = `${items.length} saved`;
            }
        } else {
            // Fallback: if we have a last-used session, fetch it and populate a single option
            const last = localStorage.getItem('interviewSessionId');
            if (last) {
                try {
                    const sres = await fetch(`/session/${last}`);
                    if (sres.ok) {
                        const sdata = await sres.json();
                        const opt = document.createElement('option');
                        opt.value = sdata.session_id || last;
                        const display = sdata.name || `Session ${String(last).slice(0, 8)}`;
                        opt.textContent = display;
                        sessionsSelect.appendChild(opt);
                        sessionsSelect.value = last;
                        resumeActions.classList.remove('hidden');
                        if (sessionsCount) {
                            sessionsCount.textContent = `1 saved`;
                        }
                        return; // done
                    }
                } catch (e) {
                    // ignore and hide panel below
                }
            }
            resumeActions.classList.add('hidden');
            if (sessionsCount) {
                sessionsCount.textContent = '';
            }
        }
    } catch (err) {
        console.debug('No saved sessions found yet.');
        resumeActions.classList.add('hidden');
    }
}

function updateResumeControlsVisibility() {
    if (!resumeActions) {
        return;
    }
    refreshSessionsList();
    refreshSwitcherList();
}

// Populate the switcher in the interview header
async function refreshSwitcherList() {
    if (!switchSessionsSelect) return;
    try {
        const res = await fetch('/sessions');
        if (!res.ok) throw new Error('Failed to load sessions');
        const items = await res.json();
        switchSessionsSelect.innerHTML = '';
        if (Array.isArray(items) && items.length > 0) {
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.textContent = item.name || `Session ${String(item.id).slice(0,8)}`;
                switchSessionsSelect.appendChild(opt);
            });
            if (state.sessionId) switchSessionsSelect.value = state.sessionId;
        } else {
            // Fallback to last-known or current
            const last = localStorage.getItem('interviewSessionId');
            const opt = document.createElement('option');
            const val = last || state.sessionId;
            if (val) {
                opt.value = val;
                opt.textContent = state.sessionName || `Session ${String(val).slice(0,8)}`;
                switchSessionsSelect.appendChild(opt);
            }
        }
    } catch (err) {
        // Fallback: ensure current session appears
        switchSessionsSelect.innerHTML = '';
        if (state.sessionId) {
            const opt = document.createElement('option');
            opt.value = state.sessionId;
            opt.textContent = state.sessionName || `Session ${String(state.sessionId).slice(0,8)}`;
            switchSessionsSelect.appendChild(opt);
        }
    }
}

// Toggle and load resume/JD for the current session
function toggleDocsPanel() {
    if (!docsPanel || !state.sessionId) return;
    const willShow = docsPanel.classList.contains('hidden');
    if (willShow) {
        // Show panel immediately with loading indicators
        docsPanel.classList.remove('hidden');
        if (resumeDocEl) resumeDocEl.textContent = state.resumeText || 'Loading resume…';
        if (jobDocEl) jobDocEl.textContent = state.jobDescText || 'Loading job description…';
        loadSessionDocuments(state.sessionId).catch(() => {
            if (!state.resumeText && resumeDocEl) resumeDocEl.textContent = 'Unable to load resume.';
            if (!state.jobDescText && jobDocEl) jobDocEl.textContent = 'Unable to load job description.';
        });
    } else {
        docsPanel.classList.add('hidden');
    }
}

async function resumeSavedSession(sessionIdOverride = null) {
    const selectedId = sessionIdOverride
        || (sessionsSelect && sessionsSelect.value)
        || localStorage.getItem('interviewSessionId');
    const savedSessionId = selectedId;
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
        if (voiceTranscript) voiceTranscript.dataset.freeze = 'false';

        if (uploadSection) {
            uploadSection.classList.add('hidden');
        }
        if (loadingSection) {
            loadingSection.classList.remove('hidden');
        }

        const response = await fetch(`/session/${savedSessionId}`);
        if (!response.ok) {
            if (response.status === 404) {
                localStorage.removeItem('interviewSessionId');
                updateResumeControlsVisibility();
                await refreshSessionsList();
                await refreshSwitcherList();
                throw new Error('Saved session was not found (it may have been removed). Please pick another session.');
            }
            throw new Error('Failed to load saved session');
        }

        const data = await response.json();

        state = createInitialState();
        state.sessionId = data.session_id;
        state.sessionName = data.name || null;
        state.questions = data.questions || [];
        state.answers = data.answers || [];
        state.evaluations = data.evaluations || [];
        state.coachLevel = (data && data.coach_level) || state.coachLevel;
        state.resumeShowFeedbackOnce = true;
        const savedVoiceId = data && data.voice_settings && data.voice_settings.voice_id;
        if (savedVoiceId) state.voice.selectedVoiceId = savedVoiceId;
        await loadSessionDocuments(state.sessionId).catch(() => {});
        syncVoiceSettingsSummary();
        localStorage.setItem('interviewSessionId', state.sessionId);

        const persistedIndex = typeof data.current_question_index === 'number'
            ? data.current_question_index
            : state.answers.length;
        const clampedIndex = Math.max(0, Math.min(persistedIndex, state.questions.length));
        state.currentQuestionIndex = clampedIndex >= state.questions.length && state.questions.length > 0
            ? state.questions.length - 1
            : clampedIndex;

        hydrateVoiceMessagesFromSession(data);

        if (sessionNameEl) {
            sessionNameEl.textContent = state.sessionName || `Session ${String(state.sessionId).slice(0, 8)}`;
        }

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

        if (!hasQuestions) {
            if (interviewContainer) {
                interviewContainer.classList.remove('hidden');
            }
            currentQuestion.textContent = 'No questions available yet. Generate or add your own question to begin.';
            feedbackSection.classList.add('hidden');
            exampleSection.classList.add('hidden');
            summarySection.classList.add('hidden');
            refreshSessionsList(state.sessionId);
            refreshSwitcherList();
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
        alert(error && error.message ? error.message : 'Unable to resume the saved session. It may have expired or been removed.');
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

async function resumeSavedSessionById(sessionId) {
    if (!sessionId) {
        return;
    }
    await resumeSavedSession(sessionId);
}


async function clearSavedSession() {
    const selectedId = sessionsSelect && sessionsSelect.value ? sessionsSelect.value : localStorage.getItem('interviewSessionId');
    if (!selectedId) {
        updateResumeControlsVisibility();
        return;
    }

    const confirmed = window.confirm('This will permanently remove the selected session. Continue?');
    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`/session/${selectedId}`, { method: 'DELETE' });
        if (!response.ok && response.status !== 404) {
            throw new Error('Failed to delete saved session');
        }
    } catch (error) {
        console.error('Error clearing saved session:', error);
        alert('Unable to clear the saved session right now. Please try again.');
        return;
    }

    if (localStorage.getItem('interviewSessionId') === selectedId) {
        localStorage.removeItem('interviewSessionId');
    }
    updateResumeControlsVisibility();
    if (state.sessionId === selectedId) {
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
        await loadSessionDocuments(state.sessionId).catch(() => {});
        
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
        updateQuestionPosition();
        
    } catch (error) {
        console.error('Error generating questions:', error);
        throw error;
    }
}

function renderMarkdownish(text) {
    if (!text) return '';
    try {
        if (typeof showdown !== 'undefined') {
            const converter = new showdown.Converter();
            return converter.makeHtml(text);
        }
    } catch (_) {}
    return String(text).replace(/\n/g, '<br>');
}

function stripMarkdownish(text) {
    if (!text) return '';
    let out = String(text);
    out = out.replace(/\*\*(.*?)\*\*/g, '$1');
    out = out.replace(/\*(.*?)\*/g, '$1');
    out = out.replace(/`([^`]*)`/g, '$1');
    out = out.replace(/^#+\s*/gm, '');
    out = out.replace(/\s+/g, ' ').trim();
    return out;
}

function cleanFeedbackFragment(text) {
    if (!text) return '';
    return String(text).replace(/\s*\b\d+\.\s*$/g, '').trim();
}

function isNoiseFeedback(str) {
    if (!str) return true;
    const normalized = String(str).trim();
    if (!normalized) return true;
    return feedbackNoiseTokens.has(normalized);
}

function setCustomQuestionStatus(message, tone = 'success') {
    if (!customQuestionStatus) return;
    if (customQuestionStatusTimer) {
        clearTimeout(customQuestionStatusTimer);
        customQuestionStatusTimer = null;
    }
    customQuestionStatus.textContent = message;
    customQuestionStatus.classList.remove('hidden');
    customQuestionStatus.classList.remove('text-rose-700', 'text-green-700');
    customQuestionStatus.classList.add(tone === 'error' ? 'text-rose-700' : 'text-green-700');
    customQuestionStatusTimer = setTimeout(() => {
        customQuestionStatus.classList.add('hidden');
    }, 3000);
}

async function handleAddCustomQuestion() {
    let sid = state.sessionId || localStorage.getItem('interviewSessionId');
    if (!sid) {
        alert('Start or resume a session first.');
        return;
    }
    state.sessionId = sid;
    const text = customQuestionInput ? customQuestionInput.value.trim() : '';
    if (!text) {
        alert('Paste a question to add.');
        return;
    }

    const btn = addCustomQuestionBtn;
    const setLoading = (loading) => {
        if (!btn) return;
        const orig = btn.dataset.origLabel || btn.textContent;
        if (!btn.dataset.origLabel) btn.dataset.origLabel = orig;
        btn.disabled = !!loading;
        btn.classList.toggle('opacity-50', !!loading);
        btn.textContent = loading ? 'Adding…' : btn.dataset.origLabel;
    };

    setLoading(true);
    try {
        const res = await fetch(`/session/${sid}/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text, make_active: true })
        });
        if (!res.ok) {
            const detail = await res.text();
            throw new Error(detail || 'Failed to add question');
        }
        const data = await res.json();
        state.questions = data.questions || [];
        const idx = typeof data.current_question_index === 'number'
            ? data.current_question_index
            : (typeof data.index === 'number' ? data.index : (state.currentQuestionIndex || 0));
        state.currentQuestionIndex = Math.max(0, Math.min(idx, state.questions.length - 1));
        setVoiceEnabled(state.questions.length > 0);
        updateVoiceStatus('Ready for voice coaching', 'idle');
        displayQuestion(state.currentQuestionIndex);
        buildQuestionRail();
        updateQuestionPosition();
        refreshSessionsList(state.sessionId);
        refreshSwitcherList();
        if (customQuestionInput) customQuestionInput.value = '';
        setCustomQuestionStatus('Added to your list');
    } catch (err) {
        console.error('Error adding custom question:', err);
        if (customQuestionStatus) {
        setCustomQuestionStatus(err.message || 'Unable to add question', 'error');
    } else {
        alert(err.message || 'Unable to add question');
    }
    } finally {
        setLoading(false);
    }
}

function bindCustomQuestionControls() {
    if (!customQuestionBound) {
        if (addCustomQuestionBtn) addCustomQuestionBtn.addEventListener('click', handleAddCustomQuestion);
        if (clearCustomQuestionBtn) {
            clearCustomQuestionBtn.addEventListener('click', () => {
                if (customQuestionInput) customQuestionInput.value = '';
                if (customQuestionStatus) customQuestionStatus.classList.add('hidden');
            });
        }
        customQuestionBound = true;
    }
}

bindCustomQuestionControls();

// Display current question
function displayQuestion(index) {
    if (index >= state.questions.length) {
        displaySummary();
        return;
    }
    
    // Persist transcript for previous index if captured
    try {
        const prevIdx = state.currentQuestionIndex;
        if (Number.isInteger(prevIdx)) {
            const t = state.voice.transcriptsByIndex[prevIdx];
            if (t && state.sessionId) {
                fetch(`/session/${state.sessionId}/voice-transcript`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question_index: prevIdx, text: t })
                }).catch(() => {});
            }
        }
    } catch (_) {}

    state.currentQuestionIndex = index;
    const question = state.questions[index];
    
    currentQuestion.textContent = question;
    if (answerInput) {
        const saved = (state.answers || []).find(a => a && a.question === question);
        answerInput.value = saved ? (saved.answer || '') : '';
    }
    updateQuestionPosition();
    
    if (interviewContainer) {
        interviewContainer.classList.remove('hidden');
    }
    feedbackSection.classList.add('hidden');
    exampleSection.classList.add('hidden');
    if (exampleQuestion) {
        exampleQuestion.textContent = '';
        exampleQuestion.classList.add('hidden');
    }
    refreshSwitcherList();
    buildQuestionRail();

    // If resuming and we already have feedback for this question, show it once.
    try {
        if (state.resumeShowFeedbackOnce) {
            const ev = state.evaluations && state.evaluations[index];
            if (ev) {
                state.resumeShowFeedbackOnce = false;
                displayFeedback(ev);
            }
        }
    } catch (_) {}
}

function updateQuestionPosition() {
    if (!questionPosEl) return;
    const total = state.questions.length || 0;
    const currentOneBased = Math.min(total, (state.currentQuestionIndex || 0) + 1);
    questionPosEl.textContent = total > 0 ? `${currentOneBased} of ${total}` : '–';
    if (sessionNameEl) {
        sessionNameEl.textContent = state.sessionName || (state.sessionId ? `Session ${String(state.sessionId).slice(0,8)}` : '');
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
                answer,
                voice_transcript: state.voice && Number.isInteger(state.currentQuestionIndex)
                    ? (state.voice.transcriptsByIndex[state.currentQuestionIndex] || '')
                    : ''
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
        const cleaned = evaluation.strengths.filter(s => !isNoiseFeedback(s));
        strengthsFeedback.innerHTML = renderMarkdownish(cleaned.join('\n')) || 'No specific strengths noted.';
    } else {
        strengthsFeedback.innerHTML = renderMarkdownish(evaluation.strengths) || 'No specific strengths noted.';
    }
    
    // Format weaknesses/improvements (handling both string and array formats)
    let improv = [];
    if (Array.isArray(evaluation.weaknesses)) {
        improv = evaluation.weaknesses;
    } else if (evaluation.weaknesses) {
        improv = [evaluation.weaknesses];
    } else if (Array.isArray(evaluation.improvements)) {
        improv = evaluation.improvements;
    } else if (evaluation.improvements) {
        improv = [evaluation.improvements];
    }
    improv = improv.filter(s => !isNoiseFeedback(s));
    improvementsFeedback.innerHTML = improv.length ? renderMarkdownish(improv.join('\n')) : 'No specific improvements suggested.';
    
    // Set content and tone feedback from the detailed feedback field
    const feedbackHtml = renderMarkdownish(evaluation.feedback || '');
    if (contentFeedback) {
        if (feedbackHtml) {
            contentFeedback.innerHTML = feedbackHtml;
            contentFeedback.classList.add('prose', 'prose-indigo', 'max-w-none');
        } else {
            contentFeedback.textContent = 'No content feedback available.';
        }
    }
    const toneText = evaluation.example_improvement || evaluation.why_asked || '';
    if (toneFeedback) {
        const toneHtml = renderMarkdownish(toneText || '');
        if (toneHtml) {
            toneFeedback.innerHTML = toneHtml;
            toneFeedback.classList.add('prose', 'prose-indigo', 'max-w-none');
        } else {
            toneFeedback.textContent = 'No tone feedback available.';
        }
    }
    
    // Parity extras for voice/typed
    try {
        // Show typed answer
        const last = state.answers[state.answers.length - 1];
        if (last && last.answer) {
            if (feedbackTypedAnswerWrap) feedbackTypedAnswerWrap.classList.remove('hidden');
            if (feedbackTypedAnswer) feedbackTypedAnswer.textContent = last.answer;
        } else if (feedbackTypedAnswerWrap) {
            feedbackTypedAnswerWrap.classList.add('hidden');
        }

        // Fetch transcript + coach text for current index
        const idx = state.currentQuestionIndex;
        if (state.sessionId) {
            fetch(`/session/${state.sessionId}`)
                .then(r => (r.ok ? r.json() : Promise.reject()))
                .then(data => {
                    const vt = (data.voice_transcripts && (data.voice_transcripts[String(idx)] || data.voice_transcripts[idx])) || '';
                    if (vt) {
                        if (feedbackUserTranscriptWrap) feedbackUserTranscriptWrap.classList.remove('hidden');
                        if (feedbackUserTranscript) feedbackUserTranscript.textContent = vt;
                    } else if (feedbackUserTranscriptWrap) {
                        feedbackUserTranscriptWrap.classList.add('hidden');
                    }

                    const coach = (data.voice_agent_text && (data.voice_agent_text[String(idx)] || data.voice_agent_text[idx])) || '';
                    if (coach) {
                        if (feedbackCoachVoiceWrap) feedbackCoachVoiceWrap.classList.remove('hidden');
                        displayCoachFeedback(coach);
                    } else if (feedbackCoachVoiceWrap) {
                        feedbackCoachVoiceWrap.classList.add('hidden');
                    }
                })
                .catch(() => {
                    if (feedbackUserTranscriptWrap) feedbackUserTranscriptWrap.classList.add('hidden');
                    if (feedbackCoachVoiceWrap) feedbackCoachVoiceWrap.classList.add('hidden');
                });
        }
    } catch (_) {}

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
    updateQuestionPosition();
}

// Coach feedback formatting similar to Example Answer
function buildCoachFeedbackMarkdown(raw, question) {
    if (!raw || typeof raw !== 'string') return '';
    const text = raw.trim();
    const parts = { situation: '', task: '', action: '', result: '', impact: '' };
    try {
        const re = /(\b\d+\.\s*)?(situation|task|action|result|impact)\s*:\s*(.*?)(?=(?:\b\d+\.\s*)?(?:situation|task|action|result|impact)\s*:|$)/gims;
        let m;
        while ((m = re.exec(text)) !== null) {
            const key = (m[2] || '').toLowerCase();
            const value = cleanFeedbackFragment(m[3] || '');
            if (parts.hasOwnProperty(key)) parts[key] = value;
        }
    } catch (_) {}

    let refined = '';
    const rIdx = text.toLowerCase().indexOf("here's a refined version:");
    if (rIdx >= 0) {
        const after = text.slice(rIdx + "here's a refined version:".length);
        const tipBreak = after.toLowerCase().indexOf("here's a tip:");
        refined = cleanFeedbackFragment(tipBreak >= 0 ? after.slice(0, tipBreak) : after);
    }
    let tip = '';
    const tIdx = text.toLowerCase().indexOf("here's a tip:");
    if (tIdx >= 0) tip = cleanFeedbackFragment(text.slice(tIdx + "here's a tip:".length));

    let md = '## Coach Feedback\n\n';
    if (question) md += `Question: ${question}\n\n`;
    if (refined) md += refined + "\n\n";
    ['situation','task','action','result','impact'].forEach((k) => {
        const v = cleanFeedbackFragment(parts[k]);
        if (v) {
            const label = k.charAt(0).toUpperCase() + k.slice(1);
            md += `**${label}:** ${v}\n`;
        }
    });
    if (tip) md += `\n**Tip:** ${tip}\n`;
    return md.trim();
}

function displayCoachFeedback(raw) {
    if (!feedbackCoachVoice) return;
    const q = state.questions && state.questions[state.currentQuestionIndex];
    const md = buildCoachFeedbackMarkdown(raw, q || '');
    if (!md) { feedbackCoachVoice.textContent = raw || ''; return; }
    if (typeof showdown === 'undefined') { feedbackCoachVoice.textContent = md; return; }
    const converter = new showdown.Converter();
    feedbackCoachVoice.innerHTML = converter.makeHtml(md);
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
    // Persist transcript for current question if any
    try {
        const currIdx = state.currentQuestionIndex;
        const t = state.voice.transcriptsByIndex[currIdx];
        if (t && state.sessionId) {
            fetch(`/session/${state.sessionId}/voice-transcript`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_index: currIdx, text: t })
            }).catch(() => {});
        }
    } catch (_) {}

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
    const totalScore = state.evaluations.reduce((sum, ev) => sum + (ev.score || 0), 0);
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
    
    state.evaluations.forEach(ev => {
        if (ev.strengths) {
            if (Array.isArray(ev.strengths)) {
                ev.strengths.forEach(s => { if (!isNoiseFeedback(s)) strengths.add(stripMarkdownish(s)); });
            } else if (!isNoiseFeedback(ev.strengths)) {
                strengths.add(stripMarkdownish(ev.strengths));
            }
        }
        if (ev.weaknesses) {
            if (Array.isArray(ev.weaknesses)) {
                ev.weaknesses.forEach(w => { if (!isNoiseFeedback(w)) improvements.add(stripMarkdownish(w)); });
            } else if (!isNoiseFeedback(ev.weaknesses)) {
                improvements.add(stripMarkdownish(ev.weaknesses));
            }
        }
        if (ev.improvements && !ev.weaknesses) {
            if (Array.isArray(ev.improvements)) {
                ev.improvements.forEach(w => { if (!isNoiseFeedback(w)) improvements.add(stripMarkdownish(w)); });
            } else if (!isNoiseFeedback(ev.improvements)) {
                improvements.add(stripMarkdownish(ev.improvements));
            }
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
    updateQuestionPosition();
    buildPerQuestionCards();
}

function buildPerQuestionCards() {
    const cardsHost = document.getElementById('per-question-cards');
    if (!cardsHost || !state.sessionId) return;
    cardsHost.innerHTML = '';

    fetch(`/session/${state.sessionId}`)
        .then(r => (r.ok ? r.json() : Promise.reject(new Error('Failed to load session details'))))
        .then(data => {
            const questions = data.questions || [];
            const evals = (data.per_question && data.per_question.length) ? data.per_question : (data.evaluations || []);
            const transcripts = data.voice_transcripts || {};
            const coachTexts = data.voice_agent_text || {};
            cardsHost.innerHTML = '';

            questions.forEach((q, i) => {
                const ev = evals[i] || {};
                const score = typeof ev.score === 'number' ? ev.score : '';
                const strengths = Array.isArray(ev.strengths) ? ev.strengths : (ev.strengths ? [ev.strengths] : []);
                const weaknesses = Array.isArray(ev.weaknesses) ? ev.weaknesses : (ev.weaknesses ? [ev.weaknesses] : []);
                const why = ev.why_asked || '';
                const example = ev.example_improvement || '';
                const t = transcripts[String(i)] || '';

                const card = document.createElement('div');
                card.className = 'p-4 border border-gray-200 rounded-lg bg-white';

                const header = document.createElement('div');
                header.className = 'flex items-center justify-between mb-2';
                header.innerHTML = `<div class="font-medium text-gray-900">Q${i + 1}: ${escapeHtml(q)}</div><div class="text-sm text-indigo-700 font-semibold">${score !== '' ? `${score}/10` : ''}</div>`;
                card.appendChild(header);

                if (why) {
                    const whyEl = document.createElement('p');
                    whyEl.className = 'text-sm text-gray-600 mb-2';
                    whyEl.textContent = `Why asked: ${why}`;
                    card.appendChild(whyEl);
                }

                if (strengths.length) {
                    const s = document.createElement('div');
                    s.className = 'mb-2';
                    s.innerHTML = '<div class="text-sm font-medium text-green-700 mb-1">What went well</div>' +
                        '<ul class="list-disc list-inside text-sm text-gray-800">' + strengths.map(escapeHtml).map(x => `<li>${x}</li>`).join('') + '</ul>';
                    card.appendChild(s);
                }

                if (weaknesses.length) {
                    const w = document.createElement('div');
                    w.className = 'mb-2';
                    w.innerHTML = '<div class="text-sm font-medium text-amber-700 mb-1">What to improve</div>' +
                        '<ul class="list-disc list-inside text-sm text-gray-800">' + weaknesses.map(escapeHtml).map(x => `<li>${x}</li>`).join('') + '</ul>';
                    card.appendChild(w);
                }

                if (example) {
                    const ex = document.createElement('details');
                    ex.className = 'mb-2';
                    ex.innerHTML = `<summary class="cursor-pointer text-sm text-gray-700">Example improvement</summary><div class="mt-2 text-sm text-gray-800 whitespace-pre-wrap">${escapeHtml(example)}</div>`;
                    card.appendChild(ex);
                }

                if (t) {
                    const tr = document.createElement('details');
                    tr.className = 'mb-1';
                    tr.innerHTML = `<summary class="cursor-pointer text-sm text-gray-700">View full transcript</summary><pre class="mt-2 whitespace-pre-wrap text-sm text-gray-800">${escapeHtml(t)}</pre>`;
                    card.appendChild(tr);
                }

                const coach = coachTexts[String(i)] || '';
                if (coach) {
                    const cf = document.createElement('details');
                    cf.className = 'mb-1';
                    const md = buildCoachFeedbackMarkdown(coach, q || '');
                    if (typeof showdown !== 'undefined' && md) {
                        const conv = new showdown.Converter();
                        const html = conv.makeHtml(md);
                        cf.innerHTML = `<summary class="cursor-pointer text-sm text-gray-700">Coach feedback (voice)</summary><div class=\"mt-2 prose prose-indigo max-w-none text-sm text-gray-800\">${html}</div>`;
                    } else {
                        cf.innerHTML = `<summary class=\"cursor-pointer text-sm text-gray-700\">Coach feedback (voice)</summary><pre class=\"mt-2 whitespace-pre-wrap text-sm text-gray-800\">${escapeHtml(coach)}</pre>`;
                    }
                    card.appendChild(cf);
                }

                cardsHost.appendChild(card);
            });
        })
        .catch(err => {
            console.debug('Per-question cards unavailable:', err);
        });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#039;');
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

// Additional UX helpers per wireframes
function startNewInterviewFlow() {
    try { stopVoiceInterview({ silent: true }); } catch (_) {}
    state = createInitialState();
    localStorage.removeItem('interviewSessionId');
    if (interviewSection) interviewSection.classList.add('hidden');
    if (summarySection) summarySection.classList.add('hidden');
    if (uploadSection) uploadSection.classList.remove('hidden');
    updateResumeControlsVisibility();
}

function toggleMuteVoice() {
    if (!state || !state.voice || !state.voice.localStream) return;
    const tracks = state.voice.localStream.getAudioTracks();
    const currentlyEnabled = tracks.some(t => t.enabled);
    tracks.forEach(t => (t.enabled = !currentlyEnabled));
    if (muteVoiceBtn) muteVoiceBtn.textContent = currentlyEnabled ? 'Unmute' : 'Mute';
}

function buildQuestionRail() {
    const host = questionRailList;
    const hostDrawer = questionDrawerList;
    if (!state || !Array.isArray(state.questions)) return;
    const renderInto = (ul) => {
        if (!ul) return;
        ul.innerHTML = '';
        state.questions.forEach((q, i) => {
            const li = document.createElement('li');
            li.title = q;
            const answered = Array.isArray(state.answers) && state.answers.some(a => a && a.question === q);
            const hasTranscript = !!(state.voice && state.voice.transcriptsByIndex && state.voice.transcriptsByIndex[i]);
            const flagged = !!(state.reviewFlags && state.reviewFlags[i]);
            const classes = ['flex','items-center','justify-between','px-2','py-1','rounded-md','cursor-pointer'];
            if (i === state.currentQuestionIndex) classes.push('bg-indigo-50','text-indigo-700');
            li.className = classes.join(' ');
            const span = document.createElement('span');
            span.textContent = `${i+1}. ${q}`;
            span.title = q;
            span.className = 'truncate';
            const badge = document.createElement('span');
            badge.textContent = flagged ? 'Review' : (answered ? 'Answered' : (hasTranscript ? 'In progress' : 'Not started'));
            badge.className = 'ml-2 text-xs text-gray-500';
            li.appendChild(span); li.appendChild(badge);
            li.addEventListener('click', () => {
                displayQuestion(i);
                if (questionDrawer) questionDrawer.classList.add('hidden');
            });
            ul.appendChild(li);
        });
        const progressMini = document.getElementById('progress-mini');
        if (progressMini) {
            const answeredCount = state.answers.length || 0;
            progressMini.textContent = `${answeredCount}/${state.questions.length}`;
        }
    };
    renderInto(host);
    renderInto(hostDrawer);
}

function toggleMarkForReview() {
    const idx = state.currentQuestionIndex;
    if (!Number.isInteger(idx)) return;
    state.reviewFlags[idx] = !state.reviewFlags[idx];
    buildQuestionRail();
}

async function refreshSessionsModalList(filter) {
    try {
        const res = await fetch('/sessions');
        if (!res.ok) throw new Error('Failed to load sessions');
        const items = await res.json();
        if (sessionsModalSelect) {
            sessionsModalSelect.innerHTML = '';
            const term = String(filter || '').toLowerCase();
            (items || []).filter(it => !term || String(it.name||'').toLowerCase().includes(term)).forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id; opt.textContent = item.name || `Session ${String(item.id).slice(0,8)}`;
                sessionsModalSelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.debug('Sessions modal list failed', err);
        if (sessionsModalSelect) sessionsModalSelect.innerHTML = '';
    }
}

function syncVoiceSettingsDrawer() {
    if (!state || !state.voice) return;
    if (toggleBrowserAsr2) toggleBrowserAsr2.checked = !!(state.voice.config && state.voice.config.useBrowserAsr);
    if (toggleShowMetadata2) toggleShowMetadata2.checked = !!(state.voice.config && state.voice.config.showMetadata);
    if (coachLevelSelect && coachLevelSelect2) coachLevelSelect2.value = coachLevelSelect.value;
    // Voices population handled by populateVoiceSettingsDrawer()
}

async function populateVoiceSettingsDrawer() {
    if (voiceSelect2Status) {
        voiceSelect2Status.textContent = 'Loading voices…';
        voiceSelect2Status.className = 'text-xs text-gray-500';
    }
    if (voiceSelect2Retry) voiceSelect2Retry.classList.add('hidden');
    try {
        const voices = await ensureVoicesCatalog();
        if (voiceSelect2) {
            voiceSelect2.innerHTML = '';
            if (voices.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'No voices available';
                voiceSelect2.appendChild(opt);
            } else {
                voices.forEach(v => {
                    const o = document.createElement('option');
                    o.value = v.id;
                    o.textContent = v.label || v.id;
                    if (v.preview_url) o.dataset.previewUrl = v.preview_url;
                    voiceSelect2.appendChild(o);
                });
                // default to main select selection if any
                if (voiceSelect && voiceSelect.value) voiceSelect2.value = voiceSelect.value;
            }
        }
        syncVoiceSettingsDrawer();
        if (voiceSelect2Status) voiceSelect2Status.textContent = '';
    } catch (err) {
        if (voiceSelect2Status) {
            voiceSelect2Status.textContent = 'Failed to load voices.';
            voiceSelect2Status.className = 'text-xs text-rose-600';
        }
        if (voiceSelect2Retry) {
            voiceSelect2Retry.classList.remove('hidden');
            voiceSelect2Retry.onclick = async () => {
                await populateVoiceSettingsDrawer();
            };
        }
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (!state || !state.questions || state.questions.length === 0) return;
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
    const k = e.key.toLowerCase();
    if (k === 'j' || e.key === 'ArrowRight') {
        e.preventDefault();
        handleNextQuestion();
    } else if (k === 'k' || e.key === 'ArrowLeft') {
        e.preventDefault();
        if (state.currentQuestionIndex > 0) displayQuestion(state.currentQuestionIndex - 1);
    } else if (k === 'v') {
        e.preventDefault();
        if (state.voice && state.voice.peer) { stopVoiceInterview(); } else { startVoiceInterview(); }
    } else if (k === 'm') {
        e.preventDefault(); toggleMuteVoice();
    } else if (k === 'e') {
        e.preventDefault(); exportFullTranscript();
    } else if (k === 'g') {
        e.preventDefault(); buildQuestionRail(); if (questionDrawer) questionDrawer.classList.remove('hidden');
    }
});
