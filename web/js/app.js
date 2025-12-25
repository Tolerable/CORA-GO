/**
 * CORA-GO - Mobile Control Panel
 * Unity Lab AI + AI-Ministries
 */

// ========== STATE ==========
const state = {
    messages: [],
    currentTab: 'chatTab',
    pcOnline: false,
    backend: 'pollinations'
};

// ========== DOM ELEMENTS ==========
const messagesEl = document.getElementById('messages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const pcStatusDot = document.getElementById('pcStatus');
const pcOnlineBadge = document.getElementById('pcOnline');
const pcInfoEl = document.getElementById('pcInfo');
const toolResultEl = document.getElementById('toolResult');
const toolOutputEl = document.getElementById('toolOutput');

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    setupEventListeners();
    setupTabs();
    addMessage('ai', 'CORA-GO ready. Tap PC tab to connect to your desktop.');

    if (Relay.isConfigured()) {
        startPCPolling();
    }
});

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', e => {
        if (e.key === 'Enter') sendMessage();
    });
    micBtn.addEventListener('click', toggleVoiceInput);
    settingsBtn.addEventListener('click', openSettings);
    settingsModal.addEventListener('click', e => {
        if (e.target === settingsModal) closeSettings();
    });
}

function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === tabId);
    });
    state.currentTab = tabId;
}

// ========== MESSAGES ==========
function addMessage(role, text) {
    state.messages.push({ role, text, time: new Date() });
    const div = document.createElement('div');
    div.className = 'message ' + role;
    div.innerHTML = '<div class="sender">' + (role === 'user' ? 'You' : 'CORA-GO') + '</div>' +
                    '<div class="text">' + escapeHtml(text) + '</div>';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== SEND MESSAGE ==========
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    userInput.value = '';
    addMessage('user', text);
    showTyping();

    try {
        let response;
        if (state.backend === 'pc' && state.pcOnline) {
            response = await Relay.runTool('ask_ai', { prompt: text });
            response = response.response || response.error || 'No response';
        } else {
            response = await queryPollinations(text);
        }
        hideTyping();
        addMessage('ai', response);
    } catch (err) {
        hideTyping();
        addMessage('ai', 'Error: ' + err.message);
    }
}

async function queryPollinations(prompt) {
    const systemPrompt = 'You are CORA-GO, a mobile AI assistant and control panel. Keep responses concise.';

    try {
        const resp = await fetch('https://text.pollinations.ai/openai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'openai',
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: prompt }
                ],
                seed: Date.now()
            })
        });

        const data = await resp.json();
        let text = data.choices && data.choices[0] && data.choices[0].message
            ? data.choices[0].message.content : 'No response';
        text = text.replace(/\n---\n\*\*Support Pollinations.*/s, '');
        return text.trim();
    } catch (e) {
        return 'Error: ' + e.message;
    }
}

function showTyping() {
    const div = document.createElement('div');
    div.id = 'typing';
    div.className = 'message ai typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById('typing');
    if (el) el.remove();
}

// ========== VOICE INPUT ==========
function toggleVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Speech recognition not supported');
        return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => micBtn.classList.add('active');
    recognition.onend = () => micBtn.classList.remove('active');
    recognition.onresult = e => {
        userInput.value = e.results[0][0].transcript;
        sendMessage();
    };

    recognition.start();
}

// ========== PC STATUS ==========
function startPCPolling() {
    Relay.startPolling(updatePCStatus, 5000);
}

function updatePCStatus(status) {
    const online = status && !status.error && status.online;
    state.pcOnline = online;

    pcStatusDot.className = 'status-dot ' + (online ? 'online' : 'offline');
    pcOnlineBadge.className = 'badge ' + (online ? 'online' : 'offline');
    pcOnlineBadge.textContent = online ? 'Online' : 'Offline';

    if (online && status.system_info) {
        const info = status.system_info;
        pcInfoEl.innerHTML =
            '<div><strong>GPU:</strong> ' + (info.gpu || 'N/A') + '</div>' +
            '<div><strong>RAM:</strong> ' + (info.ram_available_gb || '?') + 'GB free</div>' +
            '<div><strong>CPU:</strong> ' + (info.cpu_percent || '?') + '%</div>';
    } else {
        pcInfoEl.innerHTML = '<p class="muted">PC not connected</p>';
    }
}

// ========== TOOL EXECUTION ==========
async function runTool(toolName, params) {
    if (!Relay.isConfigured()) {
        alert('Configure Supabase in settings first');
        return;
    }
    if (!state.pcOnline) {
        alert('PC is offline');
        return;
    }

    toolResultEl.classList.remove('hidden');
    toolOutputEl.textContent = 'Running...';

    try {
        const result = await Relay.runTool(toolName, params || {});
        toolOutputEl.textContent = JSON.stringify(result, null, 2);
    } catch (e) {
        toolOutputEl.textContent = 'Error: ' + e.message;
    }
}

// ========== BOT CONTROL ==========
async function launchBot(botName) {
    if (!state.pcOnline) {
        alert('PC is offline');
        return;
    }
    alert('Launching ' + botName + '...');
    // TODO: Send command to PC
}

function refreshBots() {
    alert('Refreshing bots...');
}

function sendToBot() {
    const bot = document.getElementById('botSelect').value;
    const msg = document.getElementById('botMessage').value;
    if (!bot || !msg) {
        alert('Select a bot and enter a message');
        return;
    }
    alert('Sending to ' + bot + ': ' + msg);
    document.getElementById('botMessage').value = '';
}

// ========== SETTINGS ==========
function openSettings() {
    settingsModal.classList.remove('hidden');
    document.getElementById('supabaseUrl').value = Relay.url;
    document.getElementById('supabaseKey').value = Relay.key;
    document.getElementById('backendSelect').value = state.backend;
}

function closeSettings() {
    const url = document.getElementById('supabaseUrl').value.trim();
    const key = document.getElementById('supabaseKey').value.trim();

    if (url && key) {
        Relay.configure(url, key);
        startPCPolling();
    }

    state.backend = document.getElementById('backendSelect').value;
    saveSettings();
    settingsModal.classList.add('hidden');
}

async function testConnection() {
    const url = document.getElementById('supabaseUrl').value.trim();
    const key = document.getElementById('supabaseKey').value.trim();

    if (!url || !key) {
        alert('Enter URL and key first');
        return;
    }

    Relay.configure(url, key);
    const ok = await Relay.testConnection();
    alert(ok ? 'Connected!' : 'Failed');
    if (ok) startPCPolling();
}

function saveSettings() {
    localStorage.setItem('cora-go-settings', JSON.stringify({ backend: state.backend }));
}

function loadSettings() {
    const saved = localStorage.getItem('cora-go-settings');
    if (saved) {
        state.backend = JSON.parse(saved).backend || 'pollinations';
    }
}
