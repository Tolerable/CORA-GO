"""
CORA-GO Memory Tools
Working memory for storing/recalling data across sessions.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from . import register_tool
from ..config import config

# Get storage directory from config
def _get_memory_dir() -> Path:
    """Get memory storage directory."""
    storage_dir = config.get("memory.storage_dir", "memory")
    # Relative to anchor directory
    mem_dir = Path(__file__).parent.parent / storage_dir
    mem_dir.mkdir(exist_ok=True)
    return mem_dir


def _get_memory_file() -> Path:
    """Get working memory file path."""
    return _get_memory_dir() / "working_memory.json"


def _load_memory() -> dict:
    """Load memory from file."""
    mem_file = _get_memory_file()
    if mem_file.exists():
        try:
            return json.loads(mem_file.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_memory(data: dict) -> None:
    """Save memory to file."""
    mem_file = _get_memory_file()
    mem_file.write_text(json.dumps(data, indent=2))


def remember(key: str, value: Any) -> dict:
    """
    Store something in working memory.

    Args:
        key: Memory key (string identifier)
        value: Value to store (any JSON-serializable type)

    Returns:
        Status dict
    """
    if not config.get("memory.enabled", True):
        return {"error": "Memory disabled in config"}

    data = _load_memory()
    data[key] = {
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "updated_count": data.get(key, {}).get("updated_count", 0) + 1
    }
    _save_memory(data)
    return {"status": "remembered", "key": key}


def recall(key: Optional[str] = None) -> dict:
    """
    Recall from working memory.

    Args:
        key: Specific key to recall, or None for all

    Returns:
        Memory value(s)
    """
    if not config.get("memory.enabled", True):
        return {"error": "Memory disabled in config"}

    data = _load_memory()

    if key:
        entry = data.get(key)
        if entry:
            return {"key": key, "value": entry.get("value"), "timestamp": entry.get("timestamp")}
        return {"error": f"Key '{key}' not found"}

    # Return all keys with values
    return {
        "memories": {k: v.get("value") for k, v in data.items()},
        "count": len(data)
    }


def forget(key: str) -> dict:
    """
    Remove something from working memory.

    Args:
        key: Memory key to forget

    Returns:
        Status dict
    """
    if not config.get("memory.enabled", True):
        return {"error": "Memory disabled in config"}

    data = _load_memory()
    if key in data:
        del data[key]
        _save_memory(data)
        return {"status": "forgotten", "key": key}
    return {"error": f"Key '{key}' not found"}


def clear_memory() -> dict:
    """
    Clear all working memory.

    Returns:
        Status dict with count of cleared items
    """
    if not config.get("memory.enabled", True):
        return {"error": "Memory disabled in config"}

    data = _load_memory()
    count = len(data)
    _save_memory({})
    return {"status": "cleared", "items_removed": count}


def list_memories() -> dict:
    """
    List all memory keys with metadata.

    Returns:
        List of memory entries with keys and timestamps
    """
    if not config.get("memory.enabled", True):
        return {"error": "Memory disabled in config"}

    data = _load_memory()
    memories = []
    for key, entry in data.items():
        memories.append({
            "key": key,
            "timestamp": entry.get("timestamp"),
            "updated_count": entry.get("updated_count", 1),
            "value_preview": str(entry.get("value", ""))[:50]
        })

    # Sort by timestamp, newest first
    memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"memories": memories, "count": len(memories)}


# Register tools
register_tool(
    name="remember",
    description="Store something in working memory for later recall",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Memory key/name"},
            "value": {"type": "string", "description": "Value to store"},
        },
        "required": ["key", "value"],
    },
    func=remember,
)

register_tool(
    name="recall",
    description="Recall from working memory",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to recall (empty for all)"},
        },
        "required": [],
    },
    func=recall,
)

register_tool(
    name="forget",
    description="Remove something from working memory",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to forget"},
        },
        "required": ["key"],
    },
    func=forget,
)

register_tool(
    name="clear_memory",
    description="Clear all working memory",
    parameters={"type": "object", "properties": {}, "required": []},
    func=clear_memory,
)

register_tool(
    name="list_memories",
    description="List all stored memories with metadata",
    parameters={"type": "object", "properties": {}, "required": []},
    func=list_memories,
)
