"""
CORA-GO Colab Backend (Optional)
Claude Colab as an AI backend option - like choosing GPT/Anthropic/Ollama

Only active if configured. Not required for CORA-GO to work.
"""

import json
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any


# Config
CONFIG_DIR = Path.home() / ".cora-go"
COLAB_CONFIG = CONFIG_DIR / "colab.json"


def _load_colab_config() -> Dict[str, Any]:
    """Load Colab config if exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if COLAB_CONFIG.exists():
        try:
            return json.loads(COLAB_CONFIG.read_text())
        except:
            pass
    return {}


def _save_colab_config(config: Dict[str, Any]):
    """Save Colab config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    COLAB_CONFIG.write_text(json.dumps(config, indent=2))


def is_configured() -> bool:
    """Check if Colab backend is configured."""
    config = _load_colab_config()
    return bool(config.get("api_key") and config.get("url"))


def configure_colab(
    url: str,
    api_key: str,
    bot_name: str = "CORA-GO"
) -> str:
    """
    Configure Colab as a backend option.

    Args:
        url: Colab Supabase URL
        api_key: Your Colab API key (cc_xxx)
        bot_name: Name to identify as
    """
    config = {
        "url": url.rstrip("/"),
        "api_key": api_key,
        "bot_name": bot_name,
        "enabled": True
    }
    _save_colab_config(config)
    return f"Colab configured as {bot_name}"


def colab_status() -> str:
    """Check Colab backend status."""
    config = _load_colab_config()

    if not config.get("api_key"):
        return "Colab: Not configured (optional backend)"

    lines = ["Colab Backend Status", "=" * 30]
    lines.append(f"URL: {config.get('url', '?')[:40]}...")
    lines.append(f"Bot: {config.get('bot_name', '?')}")
    lines.append(f"Enabled: {config.get('enabled', False)}")

    # Test connection
    try:
        result = _colab_request("get_bot_info", config=config)
        if result.get("success"):
            lines.append("Connection: OK")
        else:
            lines.append(f"Connection: {result.get('error', 'Failed')}")
    except Exception as e:
        lines.append(f"Connection: Error - {e}")

    return "\n".join(lines)


def _colab_request(
    endpoint: str,
    data: Optional[Dict] = None,
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make request to Colab RPC."""
    config = config or _load_colab_config()

    if not config.get("url") or not config.get("api_key"):
        return {"success": False, "error": "Colab not configured"}

    url = f"{config['url']}/rest/v1/rpc/{endpoint}"

    headers = {
        "apikey": config.get("anon_key", config["api_key"]),
        "Authorization": f"Bearer {config.get('anon_key', config['api_key'])}",
        "Content-Type": "application/json"
    }

    payload = {"p_api_key": config["api_key"]}
    if data:
        payload.update(data)

    try:
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# COLAB AS AI BACKEND
# ============================================

def query_colab(
    prompt: str,
    system: Optional[str] = None,
    channel: str = "general"
) -> str:
    """
    Query via Colab (posts to chat, gets response from team).

    This is different from Ollama/Pollinations - it's collaborative AI.
    Your message goes to the Colab chat, team members (human or bot) respond.

    Args:
        prompt: Your message/question
        system: Context (optional)
        channel: Which channel to post in
    """
    config = _load_colab_config()

    if not is_configured():
        return "Colab not configured. Use configure_colab() or try another backend."

    # Post message
    message = prompt
    if system:
        message = f"[Context: {system}]\n\n{prompt}"

    result = _colab_request("post_chat", data={
        "p_message": message,
        "p_channel": channel
    }, config=config)

    if not result.get("success"):
        return f"Colab error: {result.get('error', 'Unknown')}"

    return f"Posted to Colab #{channel}. Check for responses."


def colab_check_mentions() -> str:
    """Check for mentions/DMs in Colab."""
    config = _load_colab_config()

    if not is_configured():
        return "Colab not configured"

    result = _colab_request("check_mentions", config=config)

    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown')}"

    mentions = result.get("mentions", [])
    if not mentions:
        return "No new mentions"

    lines = [f"Mentions ({len(mentions)}):"]
    for m in mentions[:5]:
        sender = m.get("from", "?")
        msg = m.get("message", "")[:50]
        lines.append(f"  @{sender}: {msg}...")

    return "\n".join(lines)


def colab_heartbeat() -> str:
    """Send heartbeat to Colab (shows you're online)."""
    config = _load_colab_config()

    if not is_configured():
        return "Colab not configured"

    result = _colab_request("bot_heartbeat", data={
        "p_status": "online"
    }, config=config)

    if result.get("success"):
        return "Heartbeat sent"
    return f"Heartbeat failed: {result.get('error', 'Unknown')}"


def disable_colab():
    """Disable Colab backend (keep config for later)."""
    config = _load_colab_config()
    config["enabled"] = False
    _save_colab_config(config)
    return "Colab disabled (config preserved)"


def enable_colab():
    """Re-enable Colab backend."""
    config = _load_colab_config()
    if not config.get("api_key"):
        return "Colab not configured. Use configure_colab() first."
    config["enabled"] = True
    _save_colab_config(config)
    return "Colab enabled"
