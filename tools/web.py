"""
CORA-GO Web Operations
Search, fetch URLs, summarize
"""

import urllib.request
import urllib.parse
import json
import re
from typing import Optional


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo HTML.

    Args:
        query: Search query
        max_results: Maximum results to return
    """
    try:
        # Use DuckDuckGo HTML interface
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'CORA-GO/1.0'}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        # Parse results (simple regex extraction)
        results = []

        # Find result blocks
        pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        for i, (link, title) in enumerate(matches[:max_results]):
            # Clean up the redirect URL
            if 'uddg=' in link:
                actual_url = urllib.parse.unquote(link.split('uddg=')[1].split('&')[0])
            else:
                actual_url = link
            results.append(f"{i+1}. {title.strip()}\n   {actual_url}")

        if not results:
            return f"No results found for: {query}"

        return f"Search results for '{query}':\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"Search error: {e}"


def fetch_url(url: str, max_chars: int = 5000) -> str:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch
        max_chars: Maximum characters to return
    """
    try:
        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'CORA-GO/1.0'}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            content_type = response.headers.get('Content-Type', '')
            content = response.read()

            # Handle encoding
            if 'charset=' in content_type:
                charset = content_type.split('charset=')[1].split(';')[0]
            else:
                charset = 'utf-8'

            try:
                text = content.decode(charset)
            except:
                text = content.decode('utf-8', errors='ignore')

        # If HTML, extract text content
        if 'text/html' in content_type:
            # Remove scripts and styles
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text).strip()

        # Truncate if needed
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[Truncated - {len(text)} chars total]"

        return f"Content from {url}:\n\n{text}"
    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:
        return f"Fetch error: {e}"


def fetch_and_summarize(url: str) -> str:
    """
    Fetch a URL and summarize its content using AI.

    Args:
        url: URL to fetch and summarize
    """
    try:
        # First fetch the content
        content = fetch_url(url, max_chars=3000)

        if content.startswith("Error") or content.startswith("HTTP Error"):
            return content

        # Use Pollinations to summarize
        prompt = f"Summarize this web page content in 2-3 paragraphs:\n\n{content}"
        encoded_prompt = urllib.parse.quote(prompt)

        summary_url = f"https://text.pollinations.ai/{encoded_prompt}"
        req = urllib.request.Request(
            summary_url,
            headers={'User-Agent': 'CORA-GO/1.0'}
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            summary = response.read().decode('utf-8')

        # Clean Pollinations ads
        summary = re.sub(r'\n---\n\*\*Support Pollinations.*', '', summary, flags=re.DOTALL)
        summary = re.sub(r'\n🌸.*Pollinations.*', '', summary, flags=re.DOTALL)

        return f"Summary of {url}:\n\n{summary.strip()}"
    except Exception as e:
        return f"Summarize error: {e}"


def get_weather(city: str = "") -> str:
    """Get weather for a city using wttr.in."""
    try:
        encoded_city = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded_city}?format=j1"

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'CORA-GO/1.0'}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        current = data.get('current_condition', [{}])[0]
        area = data.get('nearest_area', [{}])[0]

        location = area.get('areaName', [{}])[0].get('value', 'Unknown')
        temp_c = current.get('temp_C', '?')
        temp_f = current.get('temp_F', '?')
        desc = current.get('weatherDesc', [{}])[0].get('value', '')
        humidity = current.get('humidity', '?')
        wind = current.get('windspeedMiles', '?')

        return f"{location}: {desc}, {temp_f}°F ({temp_c}°C), Humidity: {humidity}%, Wind: {wind} mph"
    except Exception as e:
        return f"Weather error: {e}"
