/**
 * CORA-GO - Mobile Control Panel
 * Unity Lab AI + AI-Ministries
 */

// ========== STATE ==========
const state = {
    messages: [],
    currentTab: 'chatTab',
    pcOnline: false,
    backend: 'pollinations',
    paired: false,
    anchorId: null,
    userId: null
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
    // Check pairing status first
    checkPairingStatus();
    loadSettings();
    setupEventListeners();
    setupTabs();
});

function checkPairingStatus() {
    console.log('[APP] checkPairingStatus called');
    state.paired = localStorage.getItem('cora_paired') === 'true';
    state.anchorId = localStorage.getItem('cora_anchor_id');
    state.userId = localStorage.getItem('cora_user_id');
    console.log('[APP] paired:', state.paired, 'anchorId:', state.anchorId, 'userId:', state.userId);

    const banner = document.getElementById('pairingBanner');

    if (!state.paired) {
        console.log('[APP] Not paired - showing banner');
        if (banner) banner.style.display = 'block';
        addMessage('ai', 'Welcome to CORA-GO! Tap the banner above to pair with your PC.');
        pcInfoEl.innerHTML = '<p class="muted"><a href="pair.html">Pair device to connect</a></p>';
    } else {
        console.log('[APP] Paired - starting polling');
        if (banner) banner.style.display = 'none';
        addMessage('ai', 'CORA-GO ready. Checking PC connection...');
        startPCPolling();
    }
}

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

    // Auto-refresh bots when switching to Bots tab
    if (tabId === 'botsTab' && state.pcOnline) {
        refreshBots();
    }
}

// ========== MESSAGES ==========
function addMessage(role, text, isHtml = false) {
    state.messages.push({ role, text, time: new Date() });
    const div = document.createElement('div');
    div.className = 'message ' + role;
    // Allow HTML for special messages (links, etc)
    const textContent = text.startsWith('<') ? text : escapeHtml(text);
    div.innerHTML = '<div class="sender">' + (role === 'user' ? 'You' : 'CORA-GO') + '</div>' +
                    '<div class="text">' + textContent + '</div>';
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
    console.log('[APP] startPCPolling called');
    Relay.startPolling(updatePCStatus, 5000);
}

function updatePCStatus(status) {
    console.log('[APP] updatePCStatus called with:', status);
    const online = status && !status.error && status.online;
    console.log('[APP] online:', online);
    state.pcOnline = online;

    pcStatusDot.className = 'status-dot ' + (online ? 'online' : 'offline');
    pcOnlineBadge.className = 'badge ' + (online ? 'online' : 'offline');
    pcOnlineBadge.textContent = online ? 'Online' : 'Offline';
    console.log('[APP] Updated status dot and badge');

    if (online && status.system_info) {
        const info = status.system_info;
        pcInfoEl.innerHTML =
            '<div><strong>GPU:</strong> ' + (info.gpu || 'N/A') + '</div>' +
            '<div><strong>RAM:</strong> ' + (info.ram_available_gb || '?') + 'GB free</div>' +
            '<div><strong>CPU:</strong> ' + (info.cpu_percent || '?') + '%</div>';
        console.log('[APP] Updated PC info with system_info');
    } else {
        pcInfoEl.innerHTML = '<p class="muted">PC not connected</p>';
        console.log('[APP] No system_info, showing not connected');
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
async function refreshBots() {
    if (!state.pcOnline) {
        document.getElementById('availableBots').innerHTML = '<p class="muted">Connect to PC first</p>';
        return;
    }

    document.getElementById('availableBots').innerHTML = '<p class="muted">Loading bots...</p>';
    document.getElementById('runningBots').innerHTML = '<p class="muted">Loading...</p>';

    try {
        const result = await Relay.runTool('list_bots', {});

        if (result.bots && result.bots.length > 0) {
            // Populate available bots
            let html = '<div class="bot-list">';
            let selectHtml = '<option value="">Select bot...</option>';

            result.bots.forEach(bot => {
                const statusClass = bot.running ? 'running' : 'stopped';
                const statusIcon = bot.running ? '🟢' : '⚫';
                html += `
                    <div class="bot-item ${statusClass}">
                        <span class="bot-name">${statusIcon} ${bot.name}</span>
                        <span class="bot-type">${bot.type}</span>
                        <div class="bot-actions">
                            ${bot.running
                                ? `<button class="tool-btn small" onclick="stopBot('${bot.name}')">⏹ Stop</button>`
                                : `<button class="tool-btn small" onclick="launchBot('${bot.name}')">▶ Start</button>`
                            }
                        </div>
                    </div>
                `;
                selectHtml += `<option value="${bot.name}">${bot.name}</option>`;
            });
            html += '</div>';

            document.getElementById('availableBots').innerHTML = html;
            document.getElementById('botSelect').innerHTML = selectHtml;

            // Show running bots
            const running = result.bots.filter(b => b.running);
            if (running.length > 0) {
                document.getElementById('runningBots').innerHTML = running.map(b =>
                    `<div class="bot-running">🟢 ${b.name} (PID: ${b.pid})</div>`
                ).join('');
            } else {
                document.getElementById('runningBots').innerHTML = '<p class="muted">No bots running</p>';
            }
        } else {
            document.getElementById('availableBots').innerHTML = '<p class="muted">No bots found in C:/claude</p>';
        }
    } catch (e) {
        document.getElementById('availableBots').innerHTML = `<p class="error">Error: ${e.message}</p>`;
    }
}

async function launchBot(botName) {
    if (!state.pcOnline) {
        alert('PC is offline');
        return;
    }

    addMessage('ai', `Launching ${botName}...`);

    try {
        const result = await Relay.runTool('launch_bot', { name: botName });

        if (result.success) {
            addMessage('ai', `✅ ${botName} launched (PID: ${result.pid})`);
            refreshBots(); // Refresh the list
        } else {
            addMessage('ai', `❌ Failed: ${result.error}`);
        }
    } catch (e) {
        addMessage('ai', `❌ Error: ${e.message}`);
    }
}

async function stopBot(botName) {
    if (!state.pcOnline) {
        alert('PC is offline');
        return;
    }

    addMessage('ai', `Stopping ${botName}...`);

    try {
        const result = await Relay.runTool('stop_bot', { name: botName });

        if (result.success) {
            addMessage('ai', `✅ ${botName} stopped`);
            refreshBots(); // Refresh the list
        } else {
            addMessage('ai', `❌ Failed: ${result.error}`);
        }
    } catch (e) {
        addMessage('ai', `❌ Error: ${e.message}`);
    }
}

async function sendToBot() {
    const bot = document.getElementById('botSelect').value;
    const msg = document.getElementById('botMessage').value.trim();

    if (!bot || !msg) {
        alert('Select a bot and enter a message');
        return;
    }

    if (!state.pcOnline) {
        alert('PC is offline');
        return;
    }

    addMessage('user', `@${bot}: ${msg}`);
    document.getElementById('botMessage').value = '';

    // Send via relay as a command to the bot's inbox
    try {
        const result = await Relay.runTool('write_file', {
            path: `C:/claude/${bot}/inbox/msg_${Date.now()}.txt`,
            content: msg
        });

        if (result.success !== false) {
            addMessage('ai', `Message sent to ${bot}'s inbox`);
        } else {
            addMessage('ai', `Failed to send: ${result.error || 'Unknown error'}`);
        }
    } catch (e) {
        addMessage('ai', `Error: ${e.message}`);
    }
}

// ========== SETTINGS ==========
function openSettings() {
    settingsModal.classList.remove('hidden');
    document.getElementById('backendSelect').value = state.backend;

    // Update pairing status display
    const statusText = document.getElementById('pairingStatusText');
    const pairBtn = document.getElementById('pairBtn');
    const unpairBtn = document.getElementById('unpairBtn');

    if (state.paired) {
        const anchorId = localStorage.getItem('cora_anchor_id') || 'Unknown';
        const userName = localStorage.getItem('cora_name') || '';
        statusText.innerHTML = `<span style="color: var(--ok);">Paired</span><br>` +
            `<small style="color: #888;">Anchor: ${anchorId}</small>` +
            (userName ? `<br><small style="color: #888;">User: ${userName}</small>` : '');
        pairBtn.style.display = 'none';
        unpairBtn.style.display = 'inline-block';
    } else {
        statusText.innerHTML = '<span style="color: #888;">Not paired</span>';
        pairBtn.style.display = 'inline-block';
        unpairBtn.style.display = 'none';
    }
}

function closeSettings() {
    state.backend = document.getElementById('backendSelect').value;
    saveSettings();
    settingsModal.classList.add('hidden');
}

function unpairDevice() {
    if (!confirm('Unpair this device? You will need to scan the QR code again to reconnect.')) {
        return;
    }

    // Clear all pairing data
    localStorage.removeItem('cora_paired');
    localStorage.removeItem('cora_anchor_id');
    localStorage.removeItem('cora_user_id');
    localStorage.removeItem('cora_device_id');
    localStorage.removeItem('cora_name');
    localStorage.removeItem('cora_email');
    localStorage.removeItem('cora_pairing_code');

    state.paired = false;
    state.anchorId = null;
    state.userId = null;

    closeSettings();
    location.reload();
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

// ========== CONNECTION RETRY/REPAIR ==========
async function retryConnection() {
    const retryBtn = document.getElementById('retryBtn');
    const pcError = document.getElementById('pcError');

    // Show spinning state
    if (retryBtn) retryBtn.textContent = '⏳';
    if (pcError) pcError.style.display = 'none';

    pcInfoEl.innerHTML = '<p class="muted">Retrying connection...</p>';

    // Re-init relay
    Relay.init();

    // Force immediate status check
    try {
        const status = await Relay.getPCStatus();
        updatePCStatus(status);

        if (status && !status.error && status.online) {
            addMessage('ai', '✅ PC connection restored!');
        } else {
            showConnectionError(status?.error || 'PC not responding');
        }
    } catch (e) {
        showConnectionError(e.message);
    }

    if (retryBtn) retryBtn.textContent = '🔄';
}

function showConnectionError(msg) {
    const pcError = document.getElementById('pcError');
    const pcErrorMsg = document.getElementById('pcErrorMsg');

    if (pcError && pcErrorMsg) {
        pcErrorMsg.textContent = msg || 'Connection failed';
        pcError.style.display = 'block';
    }

    pcInfoEl.innerHTML = '<p class="muted">PC not connected</p>';
}

function repairPairing() {
    // Go to pairing page to re-pair
    if (confirm('This will clear current pairing and let you re-pair. Continue?')) {
        // Clear pairing data
        localStorage.removeItem('cora_paired');
        localStorage.removeItem('cora_anchor_id');
        localStorage.removeItem('cora_user_id');
        localStorage.removeItem('cora_device_id');
        // Redirect to pair page
        window.location.href = 'pair.html';
    }
}

// Make header status dot clickable
document.addEventListener('DOMContentLoaded', () => {
    const statusDot = document.getElementById('pcStatus');
    if (statusDot) {
        statusDot.style.cursor = 'pointer';
        statusDot.addEventListener('click', retryConnection);
    }
});
