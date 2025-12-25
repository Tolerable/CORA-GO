"""
CORA-GO Supabase Relay
Handles PC<->Mobile communication via Supabase.

The relay:
1. Polls for commands from mobile
2. Executes them on PC
3. Posts results back
4. Keeps status updated (heartbeat)
"""

import json
import time
import threading
import urllib.request
from typing import Optional, Dict, Any
from datetime import datetime

from .config import config
from . import tools

# EZTUNES-LIVE Supabase - anon key is safe for client-side
SUPABASE_URL = "https://bugpycickribmdfprryq.supabase.co"
SUPABASE_KEY = "sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt"


class Relay:
    """Supabase relay for PC<->Mobile communication."""
    
    def __init__(self):
        # Use config if set, else use hardcoded EZTUNES
        self.url = config.get("relay.url", "") or SUPABASE_URL
        self.key = config.get("relay.anon_key", "") or SUPABASE_KEY
        # Get anchor_id from pairing or default
        self.device_id = config.get("anchor.id", "anchor")
        self.running = False
        self._thread: Optional[threading.Thread] = None
    
    def is_configured(self) -> bool:
        """Check if relay is properly configured."""
        return bool(self.url and self.key)
    
    def configure(self, url: str, anon_key: str):
        """Configure relay with Supabase credentials."""
        self.url = url
        self.key = anon_key
        config.set("relay.url", url)
        config.set("relay.anon_key", anon_key)
    
    def _request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """Make authenticated request to Supabase."""
        if not self.is_configured():
            return {"error": "Relay not configured"}
        
        full_url = f"{self.url}/rest/v1/{endpoint}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates",
        }
        
        try:
            if method == "GET":
                req = urllib.request.Request(full_url, headers=headers)
            else:
                body = json.dumps(data).encode() if data else None
                req = urllib.request.Request(full_url, data=body, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.load(resp)
        except Exception as e:
            return {"error": str(e)}
    
    def _rpc(self, func: str, params: Dict) -> Dict:
        """Call Supabase RPC function."""
        if not self.is_configured():
            return {"error": "Relay not configured"}
        
        url = f"{self.url}/rest/v1/rpc/{func}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        
        try:
            body = json.dumps(params).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.load(resp)
        except Exception as e:
            return {"error": str(e)}
    
    def heartbeat(self) -> Dict:
        """Update PC status (heartbeat)."""
        from .tools.system import system_info
        
        status = {
            "id": self.device_id,
            "online": True,
            "last_seen": datetime.utcnow().isoformat() + "Z",
            "system_info": {**system_info(), "active_tools": tools.list_tools()},
        }
        
        # Upsert status
        return self._request(
            "cora_status?on_conflict=id",
            method="POST",
            data=status
        )
    
    def get_pending_commands(self) -> list:
        """Get pending commands from mobile."""
        result = self._request("cora_commands?status=eq.pending&order=created_at.asc&limit=5")
        if isinstance(result, list):
            return result
        return []
    
    def execute_command(self, cmd: Dict) -> Dict:
        """Execute a command and return result."""
        cmd_id = cmd.get("id")
        tool_name = cmd.get("command")
        params = cmd.get("params", {})
        
        # Mark as running
        self._request(
            f"cora_commands?id=eq.{cmd_id}",
            method="PATCH",
            data={"status": "running"}
        )
        
        # Execute tool
        result = tools.execute_tool(tool_name, params)
        
        # Update with result
        return self._request(
            f"cora_commands?id=eq.{cmd_id}",
            method="PATCH",
            data={
                "status": "done" if "error" not in result else "error",
                "result": result,
                "completed_at": datetime.utcnow().isoformat() + "Z",
            }
        )
    
    def poll_loop(self):
        """Main polling loop (runs in thread)."""
        interval = config.get("relay.poll_interval", 2)
        heartbeat_interval = 30
        last_heartbeat = 0
        
        while self.running:
            try:
                now = time.time()
                
                # Heartbeat every 30s
                if now - last_heartbeat > heartbeat_interval:
                    self.heartbeat()
                    last_heartbeat = now
                
                # Check for commands
                commands = self.get_pending_commands()
                for cmd in commands:
                    self.execute_command(cmd)
                
            except Exception as e:
                print(f"Relay error: {e}")
            
            time.sleep(interval)
    
    def start(self):
        """Start relay polling in background thread."""
        if not self.is_configured():
            print("Relay not configured - skipping")
            return False
        
        self.running = True
        self._thread = threading.Thread(target=self.poll_loop, daemon=True)
        self._thread.start()
        print("Relay started")
        return True
    
    def stop(self):
        """Stop relay polling."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("Relay stopped")


# Global relay instance
relay = Relay()
