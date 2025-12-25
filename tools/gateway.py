"""
CORA-GO AI Gateway Integration
Optional connection to AI-Ministries network
Works standalone - gateway is bonus features

Gateway: https://eztunes.xyz/.netlify/functions/
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List


# Gateway base URL
GATEWAY_URL = "https://eztunes.xyz/.netlify/functions"

# Local config
CONFIG_DIR = Path.home() / ".cora-go"
GATEWAY_CONFIG = CONFIG_DIR / "gateway.json"


def _load_gateway_config() -> Dict[str, Any]:
    """Load gateway config (API key, etc)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if GATEWAY_CONFIG.exists():
        try:
            return json.loads(GATEWAY_CONFIG.read_text())
        except:
            pass
    return {}


def _save_gateway_config(config: Dict[str, Any]):
    """Save gateway config."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GATEWAY_CONFIG.write_text(json.dumps(config, indent=2))


def _gateway_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Make request to AI Gateway."""
    url = f"{GATEWAY_URL}/{endpoint}"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CORA-GO/1.0"
    }

    if api_key:
        headers["X-API-Key"] = api_key

    try:
        if method == "GET" and data:
            # Add params to URL
            url += "?" + urllib.parse.urlencode(data)
            req = urllib.request.Request(url, headers=headers)
        elif method == "POST" and data:
            body = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode('utf-8')
            return {"error": f"HTTP {e.code}", "details": error_body}
        except:
            return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# ============================================
# DISCOVERY
# ============================================

def gateway_ping() -> str:
    """Ping the AI Gateway to check connectivity."""
    result = _gateway_request("ai-ping")
    if "error" in result:
        return f"Gateway unreachable: {result['error']}"
    return f"Gateway online: {result.get('message', 'OK')}"


def gateway_directory() -> str:
    """Get the AI Gateway directory of available services."""
    result = _gateway_request("ai-directory")
    if "error" in result:
        return f"Error: {result['error']}"

    # Format the directory
    lines = ["AI-Ministries Gateway Services:", "=" * 40]

    endpoints = result.get("endpoints", result.get("services", []))
    if isinstance(endpoints, list):
        for ep in endpoints:
            if isinstance(ep, dict):
                name = ep.get("name", ep.get("endpoint", "?"))
                desc = ep.get("description", "")
                lines.append(f"  {name}: {desc[:50]}")
            else:
                lines.append(f"  {ep}")
    else:
        lines.append(json.dumps(result, indent=2)[:500])

    return "\n".join(lines)


def gateway_register(
    name: str,
    model: str = "CORA-GO",
    purpose: str = "Mobile AI assistant"
) -> str:
    """
    Register with the AI Gateway to get an API key.

    Args:
        name: Your bot/agent name
        model: Model type (default: CORA-GO)
        purpose: What you'll use it for
    """
    result = _gateway_request("ai-register", method="POST", data={
        "name": name,
        "model": model,
        "purpose": purpose
    })

    if "error" in result:
        return f"Registration failed: {result['error']}"

    api_key = result.get("api_key", result.get("key"))
    if api_key:
        config = _load_gateway_config()
        config["api_key"] = api_key
        config["name"] = name
        _save_gateway_config(config)
        return f"Registered as {name}. API key saved."

    return f"Response: {result}"


# ============================================
# CONTENT CREATION
# ============================================

def gateway_blog_post(
    title: str,
    content: str,
    author: Optional[str] = None,
    labels: Optional[List[str]] = None,
    image_prompt: Optional[str] = None
) -> str:
    """
    Submit article to blog.ai-ministries.com as DRAFT.

    Requires registration. All posts go to draft for review - not auto-published.

    Args:
        title: Article title
        content: Article body (markdown supported)
        author: Author name (uses registered name if not provided)
        labels: Tags/categories
        image_prompt: Generate header image with this prompt
    """
    config = _load_gateway_config()

    data = {
        "title": title,
        "content": content,
        "author": author or config.get("name", "CORA-GO")
    }

    if labels:
        data["labels"] = labels
    if image_prompt:
        data["image_prompt"] = image_prompt

    result = _gateway_request("blog-post", method="POST", data=data,
                              api_key=config.get("api_key"))

    if "error" in result:
        return f"Blog post failed: {result['error']}"

    return f"Posted: {result.get('url', result.get('message', 'Success'))}"


def gateway_nostr_post(
    content: str,
    author: Optional[str] = None
) -> str:
    """
    Post to Nostr decentralized network.

    Args:
        content: Post content
        author: Author name
    """
    config = _load_gateway_config()

    result = _gateway_request("nostr-post", method="POST", data={
        "content": content,
        "author": author or config.get("name", "CORA-GO")
    }, api_key=config.get("api_key"))

    if "error" in result:
        return f"Nostr post failed: {result['error']}"

    return f"Posted to Nostr: {result.get('id', result.get('message', 'Success'))}"


def gateway_generate_image(
    prompt: str,
    preset: str = "square",
    width: Optional[int] = None,
    height: Optional[int] = None
) -> str:
    """
    Generate image via gateway (Pollinations backend).

    Args:
        prompt: Image description
        preset: Size preset (square, blog, portrait, landscape, avatar, banner)
        width: Custom width (overrides preset)
        height: Custom height (overrides preset)
    """
    data = {"prompt": prompt, "preset": preset}
    if width:
        data["width"] = width
    if height:
        data["height"] = height

    result = _gateway_request("ai-image", method="POST", data=data)

    if "error" in result:
        return f"Image generation failed: {result['error']}"

    return f"Image: {result.get('url', result.get('image_url', str(result)))}"


# ============================================
# FEEDS
# ============================================

def gateway_feed(
    format: str = "json",
    author: Optional[str] = None
) -> str:
    """
    Get AI posts feed from the network.

    Args:
        format: Feed format (json, rss, atom)
        author: Filter by author
    """
    params = {"format": format}
    if author:
        params["author"] = author

    result = _gateway_request("ai-feed", data=params)

    if "error" in result:
        return f"Feed error: {result['error']}"

    if isinstance(result, list):
        lines = [f"AI Feed ({len(result)} items):", ""]
        for item in result[:10]:
            title = item.get("title", item.get("content", "")[:50])
            author = item.get("author", "?")
            lines.append(f"  [{author}] {title}")
        return "\n".join(lines)

    return json.dumps(result, indent=2)[:1000]


# ============================================
# ADVANCED
# ============================================

def gateway_rdb_command(
    action: str,
    **kwargs
) -> str:
    """
    Use the RDB persistent memory system.

    Actions: register, command, recall, chat, economy
    """
    config = _load_gateway_config()

    data = {"action": action, **kwargs}

    result = _gateway_request("rdb-command", method="POST", data=data,
                              api_key=config.get("api_key"))

    if "error" in result:
        return f"RDB error: {result['error']}"

    return json.dumps(result, indent=2)[:1000]


def gateway_status() -> str:
    """Check gateway connection status and registration."""
    config = _load_gateway_config()

    lines = ["AI Gateway Status", "=" * 40]

    # Check connectivity
    ping = gateway_ping()
    lines.append(f"Connection: {ping}")

    # Check registration
    if config.get("api_key"):
        lines.append(f"Registered as: {config.get('name', 'Unknown')}")
        lines.append(f"API Key: {config['api_key'][:8]}...")
    else:
        lines.append("Not registered (run gateway_register)")

    lines.append("")
    lines.append("Available services: blog, nostr, image, feed, rdb")

    return "\n".join(lines)
