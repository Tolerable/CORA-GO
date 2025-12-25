/**
 * CORA-GO Relay
 * Handles Mobile <-> PC communication via Supabase
 */

const Relay = {
    // EZTUNES-LIVE - anon key is public/safe (RLS handles security)
    url: 'https://bugpycickribmdfprryq.supabase.co',
    key: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ1Z3B5Y2lja3JpYm1kZnBycnlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk2ODQ5MzgsImV4cCI6MjA3NTI2MDkzOH0.1S1ZoV4TvhIyUjKvwYE6wZexS2aM_EMNJzV9Gn8M1CI',
    pollInterval: null,
    anchorId: null,  // Set from pairing

    // Initialize with anchor ID from localStorage
    init() {
        this.anchorId = localStorage.getItem('cora_anchor_id') || 'anchor';
    },

    // Check if device is paired
    isPaired() {
        return localStorage.getItem('cora_paired') === 'true';
    },

    // Always configured (credentials baked in)
    isConfigured() {
        return true;
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
    
    // Get PC status (filtered by anchor_id if paired)
    async getPCStatus() {
        if (!this.isPaired()) {
            return { error: 'Not paired' };
        }
        // Reinitialize anchor ID in case it changed
        this.init();
        return await this.rpc('get_cora_status', { p_anchor_id: this.anchorId });
    },
    
    // Send command to PC
    async sendCommand(command, params = {}) {
        if (!this.isPaired()) {
            return { error: 'Not paired' };
        }
        this.init();

        const result = await this.rpc('send_cora_command', {
            p_command: command,
            p_params: params,
            p_anchor_id: this.anchorId
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
