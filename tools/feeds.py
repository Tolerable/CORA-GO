"""
CORA-GO Feed Reader
RSS/Atom/JSON feed support
Useful for news, bot streams, structured data
"""

import json
import urllib.request
import xml.etree.ElementTree as ET
import re
from typing import Optional, List, Dict, Any
from datetime import datetime


# Common feed sources
DEFAULT_FEEDS = {
    "google_news": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "hacker_news": "https://hnrss.org/frontpage",
    "reddit_tech": "https://www.reddit.com/r/technology/.rss",
    "bbc_world": "http://feeds.bbci.co.uk/news/world/rss.xml"
}


def fetch_rss(url: str, max_items: int = 10) -> str:
    """
    Fetch and parse an RSS/Atom feed.

    Args:
        url: Feed URL
        max_items: Maximum items to return
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CORA-GO/1.0"}
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')

        # Parse XML
        root = ET.fromstring(content)

        items = []

        # RSS 2.0 format
        for item in root.findall('.//item')[:max_items]:
            title = item.find('title')
            link = item.find('link')
            desc = item.find('description')
            pub_date = item.find('pubDate')

            items.append({
                "title": title.text if title is not None else "",
                "link": link.text if link is not None else "",
                "description": _clean_html(desc.text) if desc is not None and desc.text else "",
                "date": pub_date.text if pub_date is not None else ""
            })

        # Atom format
        if not items:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('.//atom:entry', ns)[:max_items]:
                title = entry.find('atom:title', ns)
                link = entry.find('atom:link', ns)
                summary = entry.find('atom:summary', ns)
                updated = entry.find('atom:updated', ns)

                items.append({
                    "title": title.text if title is not None else "",
                    "link": link.get('href') if link is not None else "",
                    "description": _clean_html(summary.text) if summary is not None and summary.text else "",
                    "date": updated.text if updated is not None else ""
                })

        if not items:
            return "No items found in feed"

        # Format output
        result = [f"Feed: {url[:60]}...", f"Items: {len(items)}", ""]
        for i, item in enumerate(items, 1):
            title = item['title'][:80] if item['title'] else "(no title)"
            result.append(f"{i}. {title}")
            if item['link']:
                result.append(f"   {item['link'][:70]}")
            if item['description']:
                desc = item['description'][:100]
                result.append(f"   {desc}...")

        return "\n".join(result)

    except ET.ParseError:
        return "Error: Invalid XML/RSS format"
    except Exception as e:
        return f"Feed error: {e}"


def fetch_json_feed(url: str, max_items: int = 10) -> str:
    """
    Fetch a JSON feed (JSON Feed format or raw JSON array).

    Args:
        url: Feed URL
        max_items: Maximum items to return
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "CORA-GO/1.0",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))

        items = []

        # JSON Feed format (jsonfeed.org)
        if isinstance(data, dict) and 'items' in data:
            for item in data['items'][:max_items]:
                items.append({
                    "title": item.get('title', ''),
                    "url": item.get('url', ''),
                    "content": item.get('content_text', item.get('summary', ''))[:200],
                    "date": item.get('date_published', '')
                })

        # Raw JSON array
        elif isinstance(data, list):
            for item in data[:max_items]:
                if isinstance(item, dict):
                    # Try common field names
                    items.append({
                        "title": item.get('title', item.get('name', str(item)[:50])),
                        "url": item.get('url', item.get('link', '')),
                        "content": str(item.get('content', item.get('body', item.get('message', ''))))[:200],
                        "date": item.get('date', item.get('timestamp', item.get('created_at', '')))
                    })
                else:
                    items.append({"title": str(item)[:100], "url": "", "content": "", "date": ""})

        if not items:
            return f"Feed returned: {str(data)[:500]}"

        result = [f"JSON Feed: {url[:50]}...", f"Items: {len(items)}", ""]
        for i, item in enumerate(items, 1):
            result.append(f"{i}. {item['title'][:80]}")
            if item['url']:
                result.append(f"   {item['url'][:70]}")
            if item['content']:
                result.append(f"   {item['content'][:100]}...")

        return "\n".join(result)

    except json.JSONDecodeError:
        return "Error: Invalid JSON format"
    except Exception as e:
        return f"JSON feed error: {e}"


def get_news(source: str = "google", max_items: int = 5) -> str:
    """
    Get news from a known source.

    Args:
        source: News source (google, hacker_news, reddit, bbc)
        max_items: Number of items
    """
    source_map = {
        "google": DEFAULT_FEEDS["google_news"],
        "hn": DEFAULT_FEEDS["hacker_news"],
        "hacker_news": DEFAULT_FEEDS["hacker_news"],
        "reddit": DEFAULT_FEEDS["reddit_tech"],
        "bbc": DEFAULT_FEEDS["bbc_world"]
    }

    url = source_map.get(source.lower())
    if not url:
        return f"Unknown source: {source}. Try: google, hn, reddit, bbc"

    return fetch_rss(url, max_items)


def list_feed_sources() -> str:
    """List available feed sources."""
    lines = ["Available feed sources:", ""]
    for name, url in DEFAULT_FEEDS.items():
        lines.append(f"  {name}: {url[:50]}...")
    lines.append("")
    lines.append("Usage: get_news('google') or fetch_rss('your_url')")
    return "\n".join(lines)


def parse_feed_items(url: str) -> List[Dict[str, Any]]:
    """
    Parse feed and return structured items (for bot use).

    Args:
        url: Feed URL

    Returns:
        List of dicts with title, link, description, date
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CORA-GO/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode('utf-8')

        # Try JSON first
        try:
            data = json.loads(content)
            if isinstance(data, dict) and 'items' in data:
                return data['items']
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Parse as XML
        root = ET.fromstring(content)
        items = []

        # RSS
        for item in root.findall('.//item'):
            items.append({
                "title": _get_text(item, 'title'),
                "link": _get_text(item, 'link'),
                "description": _clean_html(_get_text(item, 'description')),
                "date": _get_text(item, 'pubDate')
            })

        # Atom
        if not items:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('.//atom:entry', ns):
                link_el = entry.find('atom:link', ns)
                items.append({
                    "title": _get_text(entry, 'atom:title', ns),
                    "link": link_el.get('href') if link_el is not None else "",
                    "description": _clean_html(_get_text(entry, 'atom:summary', ns)),
                    "date": _get_text(entry, 'atom:updated', ns)
                })

        return items

    except Exception as e:
        return [{"error": str(e)}]


def _get_text(element: ET.Element, tag: str, ns: dict = None) -> str:
    """Get text from XML element."""
    if ns:
        child = element.find(tag, ns)
    else:
        child = element.find(tag)
    return child.text if child is not None and child.text else ""


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# Bot-oriented functions

def create_json_feed(
    items: List[Dict[str, Any]],
    title: str = "CORA-GO Feed",
    description: str = "Auto-generated feed"
) -> str:
    """
    Create a JSON Feed from items (for bots to publish).

    Args:
        items: List of dicts with title, url, content_text
        title: Feed title
        description: Feed description

    Returns:
        JSON string in JSON Feed format
    """
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": title,
        "description": description,
        "items": []
    }

    for i, item in enumerate(items):
        feed["items"].append({
            "id": item.get("id", str(i)),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content_text": item.get("content", item.get("content_text", "")),
            "date_published": item.get("date", datetime.now().isoformat())
        })

    return json.dumps(feed, indent=2)


def monitor_feed(
    url: str,
    seen_file: Optional[str] = None,
    callback: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """
    Check feed for new items (for bot monitoring).

    Args:
        url: Feed URL
        seen_file: Path to file tracking seen item IDs
        callback: Function to call for each new item

    Returns:
        List of new items
    """
    from pathlib import Path

    items = parse_feed_items(url)

    if not items or 'error' in items[0]:
        return []

    # Load seen items
    seen = set()
    if seen_file:
        seen_path = Path(seen_file)
        if seen_path.exists():
            try:
                seen = set(json.loads(seen_path.read_text()))
            except:
                pass

    new_items = []
    for item in items:
        item_id = item.get('link') or item.get('title') or str(hash(str(item)))
        if item_id not in seen:
            new_items.append(item)
            seen.add(item_id)

            if callback:
                callback(item)

    # Save seen items
    if seen_file:
        Path(seen_file).write_text(json.dumps(list(seen)))

    return new_items
