"""
CORA-GO Tool Registry
Modular tools with OpenAI-compatible function calling support.
"""

from typing import Callable, Dict, List, Any, Optional
import json

# Tool registry
_TOOLS: Dict[str, Dict] = {}


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    func: Callable
) -> None:
    """Register a tool for function calling."""
    _TOOLS[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "func": func,
    }


def get_tool(name: str) -> Optional[Dict]:
    """Get tool by name."""
    return _TOOLS.get(name)


def list_tools() -> List[str]:
    """List all registered tool names."""
    return list(_TOOLS.keys())


def get_openai_tools() -> List[Dict]:
    """Get tools in OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
        }
        for t in _TOOLS.values()
    ]


def execute_tool(name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool by name with arguments."""
    tool = _TOOLS.get(name)
    if not tool:
        return {"error": f"Unknown tool: {name}"}
    try:
        return tool["func"](**args)
    except Exception as e:
        return {"error": str(e)}


# Import tool modules to register them
from . import voice       # TTS
from . import system      # System info, clipboard, processes
from . import files       # File operations
from . import ai          # Ollama, Pollinations, image generation
from . import notes       # Note taking
from . import web         # Web fetch, search
from . import memory      # Working memory
from . import screenshots # Desktop, window, web screenshots
from . import media       # Emby/Jellyfin media control
from . import nas         # NAS file access
from . import hearing     # Speech recognition
from . import vision      # Camera capture and analysis
from . import bots        # Bot management
