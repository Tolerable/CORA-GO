"""
CORA-GO Media Tools
Emby/Jellyfin media server control.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List
from datetime import datetime
from . import register_tool
from ..config import config


def _is_configured() -> bool:
    """Check if media server is configured."""
    return bool(
        config.get("media.enabled") and
        config.get("media.url") and
        config.get("media.api_key")
    )


def _get_headers() -> dict:
    """Get request headers for Emby API."""
    api_key = config.get("media.api_key", "")
    device_id = config.get("media.device_id", "cora-go")
    return {
        "X-Emby-Token": api_key,
        "X-Emby-Client": "CORA-GO",
        "X-Emby-Device-Name": "CORA-GO",
        "X-Emby-Device-Id": device_id,
        "Content-Type": "application/json",
    }


def _request(endpoint: str, method: str = "GET", data: Optional[dict] = None) -> dict:
    """Make authenticated request to media server."""
    if not _is_configured():
        return {"error": "Media server not configured. Set media.url and media.api_key in config."}

    base_url = config.get("media.url", "").rstrip("/")
    url = f"{base_url}{endpoint}"

    try:
        if data:
            body = json.dumps(data).encode()
        else:
            body = None

        req = urllib.request.Request(url, data=body, headers=_get_headers(), method=method)
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 204:
                return {"success": True}
            return json.load(resp)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _get_active_session() -> Optional[dict]:
    """Get active playback session."""
    sessions = _request("/Sessions")
    if isinstance(sessions, list):
        for session in sessions:
            if session.get("NowPlayingItem"):
                return session
    return None


def check_media() -> dict:
    """Check media server connection and status."""
    if not _is_configured():
        return {
            "configured": False,
            "error": "Media server not configured",
            "config_needed": ["media.url", "media.api_key", "media.user_id"]
        }

    result = _request("/System/Info/Public")
    if "error" in result:
        return {"configured": True, "connected": False, "error": result["error"]}

    return {
        "configured": True,
        "connected": True,
        "server_name": result.get("ServerName"),
        "version": result.get("Version"),
        "type": config.get("media.type", "emby")
    }


def now_playing() -> dict:
    """Get what's currently playing."""
    if not _is_configured():
        return {"error": "Media server not configured"}

    session = _get_active_session()
    if not session:
        return {"playing": False, "message": "Nothing playing"}

    item = session.get("NowPlayingItem", {})
    return {
        "playing": True,
        "title": item.get("Name"),
        "type": item.get("Type"),
        "artist": " / ".join(item.get("Artists", [])) if item.get("Artists") else None,
        "album": item.get("Album"),
        "series": item.get("SeriesName"),
        "episode": item.get("IndexNumber"),
        "season": item.get("ParentIndexNumber"),
        "position_ticks": session.get("PlayState", {}).get("PositionTicks"),
        "is_paused": session.get("PlayState", {}).get("IsPaused"),
    }


def play_control(command: str) -> dict:
    """
    Send playback control command.

    Args:
        command: PlayPause, Stop, NextTrack, PreviousTrack, Seek, etc.

    Returns:
        Status dict
    """
    if not _is_configured():
        return {"error": "Media server not configured"}

    session = _get_active_session()
    if not session:
        return {"error": "No active playback session"}

    session_id = session.get("Id")
    result = _request(f"/Sessions/{session_id}/Playing/{command}", method="POST")

    if "error" not in result:
        return {"success": True, "command": command}
    return result


def pause() -> dict:
    """Pause playback."""
    return play_control("Pause")


def resume() -> dict:
    """Resume/unpause playback."""
    return play_control("Unpause")


def stop() -> dict:
    """Stop playback."""
    return play_control("Stop")


def skip() -> dict:
    """Skip to next track."""
    return play_control("NextTrack")


def previous() -> dict:
    """Go to previous track."""
    return play_control("PreviousTrack")


def search_media(query: str, media_type: Optional[str] = None, limit: int = 10) -> dict:
    """
    Search for media items.

    Args:
        query: Search query
        media_type: Filter by type (Audio, Video, Episode, Movie, etc.)
        limit: Max results

    Returns:
        Search results
    """
    if not _is_configured():
        return {"error": "Media server not configured"}

    user_id = config.get("media.user_id", "")
    if not user_id:
        return {"error": "media.user_id not configured"}

    params = {
        "SearchTerm": query,
        "Limit": limit,
        "Recursive": "true",
        "Fields": "PrimaryImageAspectRatio,BasicSyncInfo",
    }
    if media_type:
        params["IncludeItemTypes"] = media_type

    query_string = urllib.parse.urlencode(params)
    result = _request(f"/Users/{user_id}/Items?{query_string}")

    if "error" in result:
        return result

    items = result.get("Items", [])
    return {
        "results": [
            {
                "id": item.get("Id"),
                "name": item.get("Name"),
                "type": item.get("Type"),
                "artist": " / ".join(item.get("Artists", [])) if item.get("Artists") else None,
                "album": item.get("Album"),
            }
            for item in items
        ],
        "total": result.get("TotalRecordCount", len(items))
    }


def play_item(item_id: str) -> dict:
    """
    Play a specific item by ID.

    Args:
        item_id: Media item ID

    Returns:
        Status dict
    """
    if not _is_configured():
        return {"error": "Media server not configured"}

    session = _get_active_session()
    if not session:
        # Try to find a client to play on
        sessions = _request("/Sessions")
        if isinstance(sessions, list) and sessions:
            session = sessions[0]
        else:
            return {"error": "No available playback session/client"}

    session_id = session.get("Id")
    result = _request(
        f"/Sessions/{session_id}/Playing",
        method="POST",
        data={"ItemIds": [item_id], "PlayCommand": "PlayNow"}
    )

    if "error" not in result:
        return {"success": True, "item_id": item_id}
    return result


def search_and_play(query: str, media_type: str = "Audio") -> dict:
    """
    Search for media and play the first result.

    Args:
        query: Search query
        media_type: Type to search for

    Returns:
        Status dict
    """
    search_result = search_media(query, media_type=media_type, limit=1)
    if "error" in search_result:
        return search_result

    results = search_result.get("results", [])
    if not results:
        return {"error": f"No results found for '{query}'"}

    item = results[0]
    play_result = play_item(item["id"])

    if "error" not in play_result:
        return {
            "success": True,
            "playing": item["name"],
            "artist": item.get("artist"),
            "type": item["type"]
        }
    return play_result


def get_playlists() -> dict:
    """Get available playlists."""
    if not _is_configured():
        return {"error": "Media server not configured"}

    user_id = config.get("media.user_id", "")
    if not user_id:
        return {"error": "media.user_id not configured"}

    params = urllib.parse.urlencode({
        "IncludeItemTypes": "Playlist",
        "Recursive": "true",
        "Fields": "ChildCount",
    })
    result = _request(f"/Users/{user_id}/Items?{params}")

    if "error" in result:
        return result

    return {
        "playlists": [
            {
                "id": item.get("Id"),
                "name": item.get("Name"),
                "item_count": item.get("ChildCount", 0),
            }
            for item in result.get("Items", [])
        ]
    }


def recent_episodes(days: int = 7, limit: int = 20) -> dict:
    """
    Get recently added TV episodes.

    Args:
        days: Look back this many days
        limit: Max results

    Returns:
        Recent episodes
    """
    if not _is_configured():
        return {"error": "Media server not configured"}

    user_id = config.get("media.user_id", "")
    if not user_id:
        return {"error": "media.user_id not configured"}

    params = urllib.parse.urlencode({
        "IncludeItemTypes": "Episode",
        "Limit": limit,
        "Recursive": "true",
        "SortBy": "DateCreated",
        "SortOrder": "Descending",
        "Fields": "SeriesName,PremiereDate",
    })
    result = _request(f"/Users/{user_id}/Items?{params}")

    if "error" in result:
        return result

    episodes = []
    for item in result.get("Items", []):
        episodes.append({
            "name": item.get("Name"),
            "series": item.get("SeriesName"),
            "season": item.get("ParentIndexNumber"),
            "episode": item.get("IndexNumber"),
            "date": item.get("PremiereDate"),
        })

    return {"episodes": episodes}


def dj_mode(mood: Optional[str] = None) -> dict:
    """
    Auto-pick music based on time or mood.

    Args:
        mood: Optional mood (chill, energy, focus, party)

    Returns:
        Status dict
    """
    hour = datetime.now().hour

    # Mood overrides time
    if mood:
        mood = mood.lower()
        if mood in ["chill", "relax", "calm"]:
            query = "ambient chill"
        elif mood in ["energy", "pump", "workout"]:
            query = "rock metal"
        elif mood in ["focus", "work", "coding"]:
            query = "instrumental electronic"
        elif mood in ["party", "fun"]:
            query = "dance pop"
        else:
            query = mood
    else:
        # Time-based
        if 5 <= hour < 9:
            query = "morning acoustic"
        elif 9 <= hour < 12:
            query = "focus instrumental"
        elif 12 <= hour < 17:
            query = "afternoon rock"
        elif 17 <= hour < 21:
            query = "evening jazz"
        else:
            query = "night ambient"

    return search_and_play(query)


# Register tools
register_tool(
    name="check_media",
    description="Check media server (Emby/Jellyfin) connection status",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_media,
)

register_tool(
    name="now_playing",
    description="Get what's currently playing on media server",
    parameters={"type": "object", "properties": {}, "required": []},
    func=now_playing,
)

register_tool(
    name="media_pause",
    description="Pause media playback",
    parameters={"type": "object", "properties": {}, "required": []},
    func=pause,
)

register_tool(
    name="media_resume",
    description="Resume media playback",
    parameters={"type": "object", "properties": {}, "required": []},
    func=resume,
)

register_tool(
    name="media_stop",
    description="Stop media playback",
    parameters={"type": "object", "properties": {}, "required": []},
    func=stop,
)

register_tool(
    name="media_skip",
    description="Skip to next track",
    parameters={"type": "object", "properties": {}, "required": []},
    func=skip,
)

register_tool(
    name="media_previous",
    description="Go to previous track",
    parameters={"type": "object", "properties": {}, "required": []},
    func=previous,
)

register_tool(
    name="search_media",
    description="Search for music, movies, TV shows on media server",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "media_type": {"type": "string", "description": "Type: Audio, Video, Episode, Movie"},
            "limit": {"type": "integer", "description": "Max results", "default": 10},
        },
        "required": ["query"],
    },
    func=search_media,
)

register_tool(
    name="play_media",
    description="Search and play media by name",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to play"},
            "media_type": {"type": "string", "description": "Type: Audio, Video", "default": "Audio"},
        },
        "required": ["query"],
    },
    func=search_and_play,
)

register_tool(
    name="get_playlists",
    description="Get available playlists",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_playlists,
)

register_tool(
    name="recent_episodes",
    description="Get recently added TV episodes",
    parameters={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Look back days", "default": 7},
            "limit": {"type": "integer", "description": "Max results", "default": 20},
        },
        "required": [],
    },
    func=recent_episodes,
)

register_tool(
    name="dj_mode",
    description="Auto-pick and play music based on time or mood",
    parameters={
        "type": "object",
        "properties": {
            "mood": {"type": "string", "description": "Mood: chill, energy, focus, party"},
        },
        "required": [],
    },
    func=dj_mode,
)
