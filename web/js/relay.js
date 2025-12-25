/**
 * CORA-GO Relay
 * Handles Mobile <-> PC communication via Supabase
 */

const Relay = {
    url: '',
    key: '',
    pollInterval: null,
    
    // Initialize from localStorage
    init() {
        const saved = localStorage.getItem('cora-relay');
        if (saved) {
            const config = JSON.parse(saved);
            this.url = config.url || '';
            this.key = config.key || '';
        }
    },
    
    // Save config
    save() {
        localStorage.setItem('cora-relay', JSON.stringify({
            url: this.url,
            key: this.key
        }));
    },
    
    // Configure relay
    configure(url, key) {
        this.url = url.replace(/\/$/, '');  // Remove trailing slash
        this.key = key;
        this.save();
    },
    
    // Check if configured
    isConfigured() {
        return !!(this.url && this.key);
    },
    
    // Make authenticated request
    async request(endpoint, method = 'GET', data = null) {
        if (!this.isConfigured()) {
            return { error: 'Relay not configured' };
        }
        
        const headers = {
            'apikey': this.key,
            'Authorization': `Bearer ${this.key}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        };
        
        const options = { method, headers };
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        try {
            const resp = await fetch(`${this.url}/rest/v1/${endpoint}`, options);
            return await resp.json();
        } catch (e) {
            return { error: e.message };
        }
    },
    
    // Call RPC function
    async rpc(func, params = {}) {
        if (!this.isConfigured()) {
            return { error: 'Relay not configured' };
        }
        
        try {
            const resp = await fetch(`${this.url}/rest/v1/rpc/${func}`, {
                method: 'POST',
                headers: {
                    'apikey': this.key,
                    'Authorization': `Bearer ${this.key}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });
            return await resp.json();
        } catch (e) {
            return { error: e.message };
        }
    },
    
    // Get PC status
    async getPCStatus() {
        return await this.rpc('get_cora_status');
    },
    
    // Send command to PC
    async sendCommand(command, params = {}) {
        const result = await this.rpc('send_cora_command', {
            p_command: command,
            p_params: params
        });
        
        if (result && !result.error) {
            // Return command ID for tracking
            return { id: result, status: 'pending' };
        }
        return result;
    },
    
    // Get command result (poll until done)
    async getCommandResult(cmdId, timeout = 30000) {
        const start = Date.now();
        
        while (Date.now() - start < timeout) {
            const result = await this.request(`cora_commands?id=eq.${cmdId}`);
            
            if (Array.isArray(result) && result.length > 0) {
                const cmd = result[0];
                if (cmd.status === 'done' || cmd.status === 'error') {
                    return cmd.result;
                }
            }
            
            // Wait before polling again
            await new Promise(r => setTimeout(r, 500));
        }
        
        return { error: 'Timeout waiting for result' };
    },
    
    // Run tool on PC and wait for result
    async runTool(toolName, params = {}) {
        const cmd = await this.sendCommand(toolName, params);
        if (cmd.error) return cmd;
        
        return await this.getCommandResult(cmd.id);
    },
    
    // Start polling for PC status
    startPolling(callback, interval = 5000) {
        this.stopPolling();
        
        const poll = async () => {
            const status = await this.getPCStatus();
            callback(status);
        };
        
        poll(); // Initial check
        this.pollInterval = setInterval(poll, interval);
    },
    
    // Stop polling
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    },
    
    // Test connection
    async testConnection() {
        const status = await this.getPCStatus();
        return !status.error;
    }
};

// Initialize on load
Relay.init();
