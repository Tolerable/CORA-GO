"""
CORA-GO AI Tools
Ollama (local) + Pollinations (cloud) with smart routing.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict
from . import register_tool, get_openai_tools

# Endpoints
OLLAMA_URL = "http://localhost:11434"
POLLINATIONS_URL = "https://text.pollinations.ai"


def check_ollama() -> dict:
    """Check if Ollama is running."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.load(resp)
            models = [m["name"] for m in data.get("models", [])]
            return {"available": True, "models": models[:10]}
    except Exception as e:
        return {"available": False, "error": str(e)}


def query_ollama(prompt: str, model: str = "llama3.2:3b", system: Optional[str] = None) -> dict:
    """Query local Ollama."""
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
            return {"response": result.get("response", ""), "model": model}
    except Exception as e:
        return {"error": str(e)}


def query_pollinations(
    prompt: str,
    model: str = "openai",
    system: Optional[str] = None,
    tools: Optional[List[Dict]] = None
) -> dict:
    """Query Pollinations.ai with optional tool calling."""
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{POLLINATIONS_URL}/openai",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.load(resp)
            msg = result.get("choices", [{}])[0].get("message", {})
            
            # Check for tool calls
            if msg.get("tool_calls"):
                return {
                    "tool_calls": msg["tool_calls"],
                    "model": model,
                }
            
            return {"response": msg.get("content", ""), "model": model}
    except Exception as e:
        return {"error": str(e)}


def ask_ai(prompt: str, backend: str = "auto", system: Optional[str] = None) -> dict:
    """
    Smart AI query with automatic backend selection.
    
    backend: auto, ollama, pollinations
    """
    if backend == "auto":
        # Try Ollama first
        status = check_ollama()
        if status.get("available"):
            result = query_ollama(prompt, system=system)
            if "error" not in result:
                return result
        # Fallback to Pollinations
        return query_pollinations(prompt, system=system)
    
    elif backend == "ollama":
        return query_ollama(prompt, system=system)
    
    else:
        return query_pollinations(prompt, system=system)


def ask_with_tools(prompt: str, system: Optional[str] = None) -> dict:
    """Query AI with all registered tools available."""
    tools = get_openai_tools()
    return query_pollinations(prompt, system=system, tools=tools)


def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """Generate an image using Pollinations.ai (free, no API key)."""
    try:
        # Pollinations image API - just encode prompt in URL
        encoded = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"

        return {
            "url": image_url,
            "prompt": prompt,
            "width": width,
            "height": height,
            "message": f"Image generated: {image_url}"
        }
    except Exception as e:
        return {"error": str(e)}


# Register tools
register_tool(
    name="generate_image",
    description="Generate an image from a text description using AI",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Description of the image to generate"},
            "width": {"type": "integer", "description": "Image width (default 1024)", "default": 1024},
            "height": {"type": "integer", "description": "Image height (default 1024)", "default": 1024},
        },
        "required": ["prompt"],
    },
    func=generate_image,
)

register_tool(
    name="check_ollama",
    description="Check if local Ollama AI is running",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_ollama,
)

register_tool(
    name="ask_ai",
    description="Ask the AI a question",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Question or prompt"},
            "backend": {"type": "string", "enum": ["auto", "ollama", "pollinations"], "default": "auto"},
        },
        "required": ["prompt"],
    },
    func=ask_ai,
)
