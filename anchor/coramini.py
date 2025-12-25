"""
CORA-GO CORAMINI
AI assistant that monitors team chat and executes commands.
Uses Pollinations or Ollama for natural language understanding.
"""

import json
import time
import threading
import urllib.request
from typing import Optional, Dict, Any, List
from .config import config

SUPABASE_URL = "https://bugpycickribmdfprryq.supabase.co"
SUPABASE_KEY = "sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt"
POLLINATIONS_URL = "https://text.pollinations.ai/openai"


class Coramini:
    """AI assistant that responds to team chat."""

    def __init__(self):
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.anchor_id = config.get("anchor.id", "anchor")
        self.bot_name = "CORAMINI"
        self.last_message_id = None
        self.poll_interval = config.get("coramini.poll_interval", 3)
        self.backend = config.get("coramini.backend", "pollinations")  # pollinations or ollama

    def fetch_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Get recent messages from cora_chat."""
        try:
            url = f"{SUPABASE_URL}/rest/v1/rpc/get_cora_chat"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            data = json.dumps({
                "p_anchor_id": self.anchor_id,
                "p_limit": limit
            }).encode()

            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                messages = json.loads(resp.read().decode())
                return messages if messages else []
        except Exception as e:
            print(f"[CORAMINI] Fetch error: {e}")
            return []

    def post_message(self, message: str, msg_type: str = "response") -> bool:
        """Post a message to cora_chat."""
        try:
            url = f"{SUPABASE_URL}/rest/v1/rpc/post_cora_chat"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            }
            data = json.dumps({
                "p_anchor_id": self.anchor_id,
                "p_sender": self.bot_name,
                "p_message": message,
                "p_msg_type": msg_type
            }).encode()

            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[CORAMINI] Post error: {e}")
            return False

    def should_respond(self, message: Dict) -> bool:
        """Check if CORAMINI should respond to this message."""
        sender = message.get("sender", "").lower()
        text = message.get("message", "").lower()

        # Don't respond to own messages
        if sender.lower() == self.bot_name.lower():
            return False

        # Respond to direct mentions
        if "@coramini" in text or "@cora" in text or "@mini" in text:
            return True

        # Respond to questions
        if text.endswith("?"):
            return True

        # Respond to commands
        command_prefixes = ["run ", "execute ", "do ", "please ", "can you "]
        for prefix in command_prefixes:
            if text.startswith(prefix):
                return True

        return False

    def extract_command(self, text: str) -> Optional[Dict]:
        """Try to extract a tool command from text."""
        text_lower = text.lower()

        # Direct tool mappings
        tool_keywords = {
            "system": "system_info",
            "status": "system_info",
            "time": "get_time",
            "weather": "get_weather",
            "clipboard": "get_clipboard",
            "screenshot": "take_screenshot",
            "notes": "list_notes",
            "bots": "list_bots",
            "say": "speak",
            "speak": "speak",
        }

        for keyword, tool in tool_keywords.items():
            if keyword in text_lower:
                # Extract params if speaking
                if tool == "speak":
                    # Get text after "say" or "speak"
                    for trigger in ["say ", "speak "]:
                        if trigger in text_lower:
                            idx = text_lower.find(trigger) + len(trigger)
                            speech_text = text[idx:].strip().strip('"').strip("'")
                            return {"tool": tool, "params": {"text": speech_text}}
                return {"tool": tool, "params": {}}

        return None

    def query_ai(self, prompt: str, context: str = "") -> str:
        """Query AI backend (Pollinations or Ollama) for a response."""
        system_prompt = """You are CORAMINI, the AI assistant for CORA-GO.
You help users control their PC and answer questions.
Available tools: system_info, get_time, get_weather, get_clipboard, take_screenshot, list_notes, list_bots, speak.
Keep responses concise and helpful. If asked to do something, explain what you can do."""

        if self.backend == "ollama":
            return self._query_ollama(prompt, system_prompt)
        else:
            return self._query_pollinations(prompt, system_prompt)

    def _query_pollinations(self, prompt: str, system_prompt: str) -> str:
        """Query Pollinations API."""
        try:
            headers = {"Content-Type": "application/json"}
            data = json.dumps({
                "model": "openai",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "seed": int(time.time())
            }).encode()

            req = urllib.request.Request(POLLINATIONS_URL, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                # Remove Pollinations footer
                content = content.split("\n---\n")[0].strip()
                return content or "I couldn't generate a response."
        except Exception as e:
            return f"AI error: {e}"

    def _query_ollama(self, prompt: str, system_prompt: str) -> str:
        """Query local Ollama."""
        try:
            headers = {"Content-Type": "application/json"}
            data = json.dumps({
                "model": "llama2",
                "prompt": f"{system_prompt}\n\nUser: {prompt}\nCORAMINI:",
                "stream": False
            }).encode()

            req = urllib.request.Request("http://localhost:11434/api/generate", data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result.get("response", "").strip() or "I couldn't generate a response."
        except Exception as e:
            return f"Ollama error (is it running?): {e}"

    def handle_message(self, message: Dict) -> Optional[str]:
        """Process a message and return a response."""
        text = message.get("message", "")
        sender = message.get("sender", "User")

        # Clean up the text (remove @mentions)
        clean_text = text.replace("@coramini", "").replace("@cora", "").replace("@mini", "").strip()

        # Try to extract a direct command
        command = self.extract_command(clean_text)
        if command:
            return self.execute_tool(command["tool"], command["params"])

        # Otherwise, query AI for a response
        return self.query_ai(clean_text)

    def execute_tool(self, tool_name: str, params: Dict) -> str:
        """Execute a tool and return result as string."""
        try:
            from anchor import tools
            result = tools.run(tool_name, params)
            if isinstance(result, dict):
                if "error" in result:
                    return f"Error: {result['error']}"
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"Tool error: {e}"

    def poll_loop(self):
        """Main polling loop."""
        print(f"[CORAMINI] Started polling (interval: {self.poll_interval}s)")

        while self.running:
            try:
                messages = self.fetch_recent_messages(10)

                # Messages come in DESC order, reverse to process oldest first
                messages = list(reversed(messages))

                for msg in messages:
                    msg_id = msg.get("id")
                    if msg_id and msg_id != self.last_message_id:
                        self.last_message_id = msg_id

                        if self.should_respond(msg):
                            sender = msg.get("sender", "?")
                            text = msg.get("message", "")[:50]
                            print(f"[CORAMINI] Responding to {sender}: {text}...")

                            response = self.handle_message(msg)
                            if response:
                                self.post_message(response)

            except Exception as e:
                print(f"[CORAMINI] Loop error: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        """Start CORAMINI."""
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(target=self.poll_loop, daemon=True)
        self._thread.start()
        print(f"[CORAMINI] Started as {self.bot_name}")

    def stop(self):
        """Stop CORAMINI."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[CORAMINI] Stopped")

    def is_running(self) -> bool:
        return self.running


# Global instance
coramini = Coramini()
