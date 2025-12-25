/**
 * CORA-GO - Main Application
 * Unity Lab AI + AI-Ministries
 */

// State
const state = {
    messages: [],
    persona: 'default',
    backend: 'auto',
    voiceEnabled: true,
    wakeWordEnabled: false,
    isListening: false,
    isSpeaking: false
};

// DOM Elements
const messagesEl = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const voiceToggle = document.getElementById('voiceToggle');
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const statusEl = document.getElementById('status');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    setupEventListeners();
    addMessage('ai', 'CORA-GO ready. How can I help?');
    setStatus('Ready');
});

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    micBtn.addEventListener('click', toggleVoiceInput);
    voiceToggle.addEventListener('click', toggleVoice);
    settingsBtn.addEventListener('click', openSettings);

    // Close modal on backdrop click
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettings();
    });
}

// Messages
function addMessage(role, text) {
    const msg = { role, text, time: new Date() };
    state.messages.push(msg);
    renderMessage(msg);
    scrollToBottom();
}

function renderMessage(msg) {
    const div = document.createElement('div');
    div.className = `message ${msg.role}`;
    div.innerHTML = `
        <div class="sender">${msg.role === 'user' ? 'You' : 'CORA-GO'}</div>
        <div class="text">${escapeHtml(msg.text)}</div>
    `;
    messagesEl.appendChild(div);
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Send Message
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    userInput.value = '';
    addMessage('user', text);
    setStatus('Thinking...');
    showTyping();

    try {
        const response = await getAIResponse(text);
        hideTyping();
        addMessage('ai', response);

        if (state.voiceEnabled) {
            speak(response);
        }
    } catch (err) {
        hideTyping();
        addMessage('ai', `Error: ${err.message}`);
    }

    setStatus('Ready');
}

// AI Response
async function getAIResponse(prompt) {
    const backend = state.backend;

    // Try Ollama first if auto or ollama
    if (backend === 'auto' || backend === 'ollama') {
        try {
            const ollamaResp = await queryOllama(prompt);
            if (ollamaResp) return ollamaResp;
        } catch (e) {
            console.log('Ollama failed, trying Pollinations');
        }
    }

    // Fallback to Pollinations
    if (backend === 'auto' || backend === 'pollinations') {
        return await queryPollinations(prompt);
    }

    throw new Error('No AI backend available');
}

async function queryOllama(prompt) {
    const response = await fetch('http://localhost:11434/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'llama3.2:3b',
            prompt: `${getPersonaPrompt()}\n\nUser: ${prompt}\n\nAssistant:`,
            stream: false
        })
    });

    if (!response.ok) throw new Error('Ollama unavailable');
    const data = await response.json();
    return data.response?.trim();
}

async function queryPollinations(prompt) {
    const systemPrompt = getPersonaPrompt();
    const url = `https://text.pollinations.ai/${encodeURIComponent(prompt)}?system=${encodeURIComponent(systemPrompt)}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error('Pollinations unavailable');

    let text = await response.text();
    // Strip Pollinations ads
    text = text.replace(/\n---\n\*\*Support Pollinations.*/s, '');
    text = text.replace(/\n🌸.*Pollinations.*/s, '');
    return text.trim();
}

function getPersonaPrompt() {
    const personas = {
        default: 'You are CORA-GO, a helpful AI assistant. Be concise and friendly.',
        worker: 'You are CORA-GO in worker mode. Focus on completing tasks efficiently.',
        sentinel: 'You are CORA-GO Sentinel. You monitor for safety and opportunities.',
        cora: 'You are CORA, a creative AI with cyberpunk personality. Be expressive.'
    };
    return personas[state.persona] || personas.default;
}

// Typing Indicator
function showTyping() {
    const div = document.createElement('div');
    div.id = 'typing';
    div.className = 'message ai typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(div);
    scrollToBottom();
}

function hideTyping() {
    const typing = document.getElementById('typing');
    if (typing) typing.remove();
}

// Voice Output (TTS)
function speak(text) {
    if (!state.voiceEnabled) return;

    // Use Web Speech API (Kokoro integration can be added later)
    if ('speechSynthesis' in window) {
        state.isSpeaking = true;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = () => { state.isSpeaking = false; };
        speechSynthesis.speak(utterance);
    }
}

function toggleVoice() {
    state.voiceEnabled = !state.voiceEnabled;
    voiceToggle.textContent = state.voiceEnabled ? '🔊' : '🔇';
    saveSettings();
}

// Voice Input (STT)
function toggleVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        setStatus('Speech recognition not supported');
        return;
    }

    if (state.isListening) {
        stopListening();
    } else {
        startListening();
    }
}

function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        state.isListening = true;
        micBtn.classList.add('active');
        setStatus('Listening...');
    };

    recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        userInput.value = text;
        sendMessage();
    };

    recognition.onerror = (e) => {
        console.error('Speech error:', e.error);
        setStatus('Speech error');
    };

    recognition.onend = () => {
        state.isListening = false;
        micBtn.classList.remove('active');
        setStatus('Ready');
    };

    recognition.start();
    window.currentRecognition = recognition;
}

function stopListening() {
    if (window.currentRecognition) {
        window.currentRecognition.stop();
    }
}

// Settings
function openSettings() {
    settingsModal.classList.remove('hidden');
    document.getElementById('personaSelect').value = state.persona;
    document.getElementById('backendSelect').value = state.backend;
    document.getElementById('voiceEnabled').checked = state.voiceEnabled;
    document.getElementById('wakeWordEnabled').checked = state.wakeWordEnabled;
}

function closeSettings() {
    state.persona = document.getElementById('personaSelect').value;
    state.backend = document.getElementById('backendSelect').value;
    state.voiceEnabled = document.getElementById('voiceEnabled').checked;
    state.wakeWordEnabled = document.getElementById('wakeWordEnabled').checked;

    settingsModal.classList.add('hidden');
    saveSettings();
}

function saveSettings() {
    localStorage.setItem('cora-go-settings', JSON.stringify({
        persona: state.persona,
        backend: state.backend,
        voiceEnabled: state.voiceEnabled,
        wakeWordEnabled: state.wakeWordEnabled
    }));
}

function loadSettings() {
    const saved = localStorage.getItem('cora-go-settings');
    if (saved) {
        const settings = JSON.parse(saved);
        Object.assign(state, settings);
        voiceToggle.textContent = state.voiceEnabled ? '🔊' : '🔇';
    }
}

// Status
function setStatus(text) {
    statusEl.textContent = text;
}
