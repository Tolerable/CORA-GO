"""
CORA-GO Web Tools
Web search, URL fetching, weather.
"""

import json
import urllib.request
import urllib.parse
import re
from typing import Optional
from . import register_tool


def web_search(query: str, num_results: int = 5) -> dict:
    """Search the web via DuckDuckGo."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        # Parse results (simple regex)
        results = []
        pattern = r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)'
        for match in re.finditer(pattern, html):
            if len(results) >= num_results:
                break
            results.append({"url": match.group(1), "title": match.group(2).strip()})
        
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}


def fetch_url(url: str, max_chars: int = 5000) -> dict:
    """Fetch URL content."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
        
        # Strip HTML tags for plain text
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return {"url": url, "content": text[:max_chars]}
    except Exception as e:
        return {"error": str(e)}


def get_weather(location: str = "auto") -> dict:
    """Get weather for location."""
    try:
        # Use wttr.in for simplicity
        loc = "" if location == "auto" else urllib.parse.quote(location)
        url = f"https://wttr.in/{loc}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        
        current = data.get("current_condition", [{}])[0]
        return {
            "location": location,
            "temp_c": current.get("temp_C"),
            "temp_f": current.get("temp_F"),
            "condition": current.get("weatherDesc", [{}])[0].get("value"),
            "humidity": current.get("humidity"),
            "wind_mph": current.get("windspeedMiles"),
        }
    except Exception as e:
        return {"error": str(e)}


# Register tools
register_tool(
    name="web_search",
    description="Search the web",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    func=web_search,
)

register_tool(
    name="fetch_url",
    description="Fetch content from a URL",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "max_chars": {"type": "integer", "default": 5000},
        },
        "required": ["url"],
    },
    func=fetch_url,
)

register_tool(
    name="get_weather",
    description="Get weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name", "default": "auto"},
        },
        "required": [],
    },
    func=get_weather,
)
