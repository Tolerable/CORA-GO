"""
CORA-GO AI Operations
Ollama (local) + Pollinations (cloud) backends
"""

import json
import urllib.request
import urllib.parse
import subprocess
import base64
import re
from pathlib import Path
from typing import Optional, List


# Default models
OLLAMA_MODELS = {
    "default": "llama3.2:3b",
    "code": "codellama:7b",
    "vision": "llava:7b",
    "fast": "llama3.2:1b"
}

POLLINATIONS_MODELS = ["openai", "mistral", "claude"]


def query_ollama(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    Query Ollama local AI.

    Args:
        prompt: User prompt
        model: Model to use (default: llama3.2:3b)
        system: System prompt (optional)
        temperature: Creativity (0.0-1.0)
    """
    try:
        model = model or OLLAMA_MODELS["default"]

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        if system:
            payload["system"] = system

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

        return result.get("response", "").strip()
    except urllib.error.URLError:
        return "Error: Ollama not running. Start with: ollama serve"
    except Exception as e:
        return f"Ollama error: {e}"


def query_pollinations(
    prompt: str,
    system: Optional[str] = None,
    model: str = "openai"
) -> str:
    """
    Query Pollinations.ai cloud API (free, no key needed).

    Args:
        prompt: User prompt
        system: System prompt (optional)
        model: Model backend (openai, mistral, claude)
    """
    try:
        # Build URL
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}"

        params = []
        if system:
            params.append(f"system={urllib.parse.quote(system)}")
        if model and model != "openai":
            params.append(f"model={model}")

        if params:
            url += "?" + "&".join(params)

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CORA-GO/1.0"}
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            text = response.read().decode('utf-8')

        # Strip Pollinations ads
        text = re.sub(r'\n---\n\*\*Support Pollinations.*', '', text, flags=re.DOTALL)
        text = re.sub(r'\n🌸.*Pollinations.*', '', text, flags=re.DOTALL)

        return text.strip()
    except Exception as e:
        return f"Pollinations error: {e}"


def analyze_image(
    image_path: str,
    prompt: str = "Describe this image in detail",
    use_ollama: bool = True
) -> str:
    """
    Analyze an image using vision AI.

    Args:
        image_path: Path to image file
        prompt: Question about the image
        use_ollama: Use local Ollama llava (True) or Pollinations (False)
    """
    try:
        path = Path(image_path).expanduser().resolve()
        if not path.exists():
            return f"Error: Image not found: {image_path}"

        if use_ollama:
            # Use Ollama llava model
            result = subprocess.run(
                ['ollama', 'run', OLLAMA_MODELS["vision"], prompt, str(path)],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Ollama vision error: {result.stderr}"
        else:
            # Use Pollinations vision API
            with open(path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Get file extension
            ext = path.suffix.lower().lstrip('.')
            if ext == 'jpg':
                ext = 'jpeg'

            data_url = f"data:image/{ext};base64,{image_data}"

            # Pollinations vision endpoint
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}}
                        ]
                    }
                ],
                "model": "openai"
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                "https://text.pollinations.ai/",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "CORA-GO/1.0"
                }
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = response.read().decode('utf-8')

            return result.strip()
    except subprocess.TimeoutExpired:
        return "Error: Image analysis timed out"
    except Exception as e:
        return f"Image analysis error: {e}"


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    output_path: Optional[str] = None
) -> str:
    """
    Generate an image using Pollinations.

    Args:
        prompt: Image description
        width: Image width
        height: Image height
        output_path: Where to save (optional, defaults to temp)
    """
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CORA-GO/1.0"}
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            image_data = response.read()

        # Determine output path
        if output_path:
            path = Path(output_path)
        else:
            import tempfile
            path = Path(tempfile.gettempdir()) / f"cora_image_{hash(prompt) % 100000}.png"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_data)

        return f"Image generated: {path}"
    except Exception as e:
        return f"Image generation error: {e}"


def list_ollama_models() -> str:
    """List available Ollama models."""
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return "Available Ollama models:\n" + result.stdout
        else:
            return f"Error listing models: {result.stderr}"
    except FileNotFoundError:
        return "Error: Ollama not installed"
    except Exception as e:
        return f"Error: {e}"
