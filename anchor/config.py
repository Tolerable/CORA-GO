"""
CORA-GO Configuration
Manages settings, paths, and API keys.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

# Paths
ANCHOR_DIR = Path(__file__).parent
PROJECT_DIR = ANCHOR_DIR.parent
DATA_DIR = ANCHOR_DIR / "data"
CONFIG_FILE = ANCHOR_DIR / "config.json"

# Ensure data dir exists
DATA_DIR.mkdir(exist_ok=True)

# Default configuration
DEFAULTS = {
    "version": "2.0.0-alpha",
    "name": "CORA-GO",
    
    # Voice settings
    "voice": {
        "engine": "kokoro",          # kokoro, pyttsx3, powershell
        "voice_id": "af_bella",      # Kokoro voice
        "rate": 1.0,                 # Speech rate multiplier
        "enabled": True,
        "speak_errors_only": True,   # Only speak problems on startup
    },
    
    # AI backends
    "ai": {
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.2:3b",
        "ollama_code": "codellama:7b",
        "ollama_vision": "llava:7b",
        "pollinations_model": "openai",
        "default_backend": "auto",   # auto, ollama, pollinations
    },
    
    # Supabase relay
    "relay": {
        "enabled": True,
        "url": "",                   # Set on first run
        "anon_key": "",
        "poll_interval": 2,          # Seconds between checks
    },
    
    # API server
    "api": {
        "enabled": True,
        "port": 7780,
        "token": "",                 # Generated on first run
    },
    
    # Safety
    "safety": {
        "blocked_commands": ["rm -rf /", "format c:", "del /s /q c:\\"],
        "confirm_commands": ["rm ", "del ", "pip install"],
        "dangerous_mode": False,
    },
}


class Config:
    """Configuration manager with auto-save."""
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load config from file, merge with defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    saved = json.load(f)
                self._config = self._merge(DEFAULTS, saved)
            except Exception:
                self._config = DEFAULTS.copy()
        else:
            self._config = DEFAULTS.copy()
            self.save()
    
    def save(self) -> None:
        """Save config to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'voice.engine')."""
        keys = key.split('.')
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val
    
    def set(self, key: str, value: Any) -> None:
        """Set config value by dot-notation key."""
        keys = key.split('.')
        obj = self._config
        for k in keys[:-1]:
            if k not in obj:
                obj[k] = {}
            obj = obj[k]
        obj[keys[-1]] = value
        self.save()
    
    def _merge(self, defaults: Dict, saved: Dict) -> Dict:
        """Deep merge saved config into defaults."""
        result = defaults.copy()
        for key, val in saved.items():
            if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = self._merge(result[key], val)
            else:
                result[key] = val
        return result


# Global config instance
config = Config()
