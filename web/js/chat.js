/**
 * CORA-GO Team Chat
 * Real-time messaging via cora_chat table
 */

const TeamChat = {
    url: 'https://bugpycickribmdfprryq.supabase.co',
    key: 'sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt',
    anchorId: null,
    userName: 'user',
    pollInterval: null,
    lastMessageId: null,
    messages: [],

    init() {
        this.anchorId = localStorage.getItem('cora_anchor_id') || 'anchor';
        this.userName = localStorage.getItem('cora_name') || 'User';
        console.log('[CHAT] Initialized for', this.anchorId);
    },

    async loadMessages(limit = 50) {
        try {
            const resp = await fetch(
                `${this.url}/rest/v1/rpc/get_cora_chat`,
                {
                    method: 'POST',
                    headers: {
                        'apikey': this.key,
                        'Authorization': `Bearer ${this.key}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        p_anchor_id: this.anchorId,
                        p_limit: limit
                    })
                }
            );
            const data = await resp.json();
            // Reverse to get chronological order (RPC returns DESC)
            this.messages = (data || []).reverse();
            return this.messages;
        } catch (e) {
            console.error('[CHAT] Load error:', e);
            return [];
        }
    },

    async postMessage(message, msgType = 'text') {
        try {
            const resp = await fetch(
                `${this.url}/rest/v1/rpc/post_cora_chat`,
                {
                    method: 'POST',
                    headers: {
                        'apikey': this.key,
                        'Authorization': `Bearer ${this.key}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        p_anchor_id: this.anchorId,
                        p_sender: this.userName,
                        p_message: message,
                        p_msg_type: msgType
                    })
                }
            );
            const id = await resp.json();
            return { success: true, id };
        } catch (e) {
            console.error('[CHAT] Post error:', e);
            return { success: false, error: e.message };
        }
    },

    async pollNew(callback) {
        const messages = await this.loadMessages(20);
        if (messages.length > 0) {
            const newestId = messages[messages.length - 1].id;
            if (this.lastMessageId !== newestId) {
                this.lastMessageId = newestId;
                callback(messages);
            }
        }
    },

    startPolling(callback, intervalMs = 3000) {
        this.init();
        // Initial load
        this.loadMessages().then(msgs => callback(msgs));
        // Poll for new messages
        this.pollInterval = setInterval(() => this.pollNew(callback), intervalMs);
    },

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },

    formatTime(timestamp) {
        const d = new Date(timestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    renderMessages(messages, container) {
        container.innerHTML = '';
        messages.forEach(msg => {
            const div = document.createElement('div');
            const isUser = msg.sender === this.userName;
            div.className = `team-message ${isUser ? 'outgoing' : 'incoming'} ${msg.msg_type}`;
            div.innerHTML = `
                <div class="msg-sender">${this.escapeHtml(msg.sender)}</div>
                <div class="msg-text">${this.escapeHtml(msg.message)}</div>
                <div class="msg-time">${this.formatTime(msg.created_at)}</div>
            `;
            container.appendChild(div);
        });
        container.scrollTop = container.scrollHeight;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Export for use
window.TeamChat = TeamChat;
