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
    // Try tool-enabled OpenAI endpoint first
    try {
        const result = await queryPollinationsWithTools(prompt);
        if (result) return result;
    } catch (e) {
        console.log('Tool calling failed, falling back to simple endpoint');
    }

    // Fallback to simple endpoint
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

// Tool definitions for Pollinations OpenAI endpoint
const CORA_TOOLS = [
    {
        type: "function",
        function: {
            name: "get_current_time",
            description: "Get the current date and time",
            parameters: {
                type: "object",
                properties: {},
                required: []
            }
        }
    },
    {
        type: "function",
        function: {
            name: "get_weather",
            description: "Get current weather for a location",
            parameters: {
                type: "object",
                properties: {
                    location: {
                        type: "string",
                        description: "City name, e.g. 'London' or 'New York'"
                    }
                },
                required: ["location"]
            }
        }
    },
    {
        type: "function",
        function: {
            name: "generate_image",
            description: "Generate an AI image from a text description",
            parameters: {
                type: "object",
                properties: {
                    prompt: {
                        type: "string",
                        description: "Description of the image to generate"
                    }
                },
                required: ["prompt"]
            }
        }
    }
];

// Execute tool calls
async function executeToolCall(name, args) {
    switch (name) {
        case 'get_current_time':
            const now = new Date();
            return JSON.stringify({
                date: now.toLocaleDateString(),
                time: now.toLocaleTimeString(),
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                day: now.toLocaleDateString('en-US', { weekday: 'long' })
            });

        case 'get_weather':
            try {
                const resp = await fetch(`https://wttr.in/${encodeURIComponent(args.location)}?format=j1`);
                if (!resp.ok) throw new Error('Weather unavailable');
                const data = await resp.json();
                const current = data.current_condition[0];
                return JSON.stringify({
                    location: args.location,
                    temp_c: current.temp_C,
                    temp_f: current.temp_F,
                    condition: current.weatherDesc[0].value,
                    humidity: current.humidity + '%',
                    wind: current.windspeedMiles + ' mph'
                });
            } catch (e) {
                return JSON.stringify({ error: 'Could not fetch weather', location: args.location });
            }

        case 'generate_image':
            const imageUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(args.prompt)}?width=512&height=512&nologo=true`;
            // Show image in chat
            setTimeout(() => {
                const imgDiv = document.createElement('div');
                imgDiv.className = 'message ai';
                imgDiv.innerHTML = `
                    <div class="sender">CORA-GO</div>
                    <div class="text"><img src="${imageUrl}" alt="${args.prompt}" style="max-width:100%;border-radius:8px;"></div>
                `;
                messagesEl.appendChild(imgDiv);
                scrollToBottom();
            }, 100);
            return JSON.stringify({ status: 'Image generated', prompt: args.prompt, url: imageUrl });

        default:
            return JSON.stringify({ error: 'Unknown tool' });
    }
}

// Query Pollinations with tool calling
async function queryPollinationsWithTools(prompt, followUpMessages = null) {
    const systemPrompt = getPersonaPrompt();

    let messages;
    if (followUpMessages) {
        messages = [{ role: 'system', content: systemPrompt }, ...followUpMessages];
    } else {
        messages = [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: prompt }
        ];
    }

    const response = await fetch('https://text.pollinations.ai/openai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: 'openai',
            messages: messages,
            tools: CORA_TOOLS,
            tool_choice: 'auto',
            seed: Date.now()
        })
    });

    if (!response.ok) throw new Error('Pollinations OpenAI unavailable');

    const data = await response.json();

    // Check for tool calls
    if (data.choices?.[0]?.message?.tool_calls?.length > 0) {
        const toolCall = data.choices[0].message.tool_calls[0];
        console.log('Tool call:', toolCall.function.name);

        try {
            const args = JSON.parse(toolCall.function.arguments);
            const result = await executeToolCall(toolCall.function.name, args);

            // Send result back to AI for natural response
            const followUp = [
                { role: 'user', content: prompt },
                { role: 'assistant', content: null, tool_calls: [toolCall] },
                { role: 'tool', tool_call_id: toolCall.id, name: toolCall.function.name, content: result }
            ];

            return await queryPollinationsWithTools(prompt, followUp);
        } catch (e) {
            console.error('Tool execution error:', e);
            return data.choices[0].message.content || 'Tool error occurred';
        }
    }

    // Regular response
    let text = data.choices?.[0]?.message?.content || '';
    text = text.replace(/\n---\n\*\*Support Pollinations.*/s, '');
    text = text.replace(/\n🌸.*Pollinations.*/s, '');
    return text.trim();
}

function getPersonaPrompt() {
    const baseContext = `You are CORA-GO, a mobile AI assistant.
You have these REAL tools available via function calling:
- get_current_time: Get the actual current date, time, and day
- get_weather: Get real weather for any city (use this when asked about weather!)
- generate_image: Generate AI images from text descriptions

IMPORTANT: Use these tools when relevant! If someone asks the time or weather, CALL THE TOOL.
Keep responses concise (2-3 sentences unless asked for more).`;

    const personas = {
        default: baseContext + ' Be helpful and friendly.',
        worker: baseContext + ' Focus on completing tasks efficiently. Minimal chat.',
        sentinel: baseContext + ' You help monitor for safety and opportunities.',
        cora: baseContext + ' You have a creative cyberpunk personality. Be expressive but honest.'
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
