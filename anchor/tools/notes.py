"""
CORA-GO Notes Tools
Persistent note storage with JSON backend.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from . import register_tool
from ..config import DATA_DIR

NOTES_FILE = DATA_DIR / "notes.json"


def _load_notes() -> List[dict]:
    """Load notes from file."""
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except Exception:
            return []
    return []


def _save_notes(notes: List[dict]):
    """Save notes to file."""
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


def add_note(content: str, tags: Optional[List[str]] = None) -> dict:
    """Add a new note."""
    notes = _load_notes()
    note = {
        "id": len(notes) + 1,
        "content": content,
        "tags": tags or [],
        "created": datetime.now().isoformat(),
    }
    notes.append(note)
    _save_notes(notes)
    return {"status": "added", "id": note["id"]}


def list_notes(limit: int = 20, tag: Optional[str] = None) -> dict:
    """List notes, optionally filtered by tag."""
    notes = _load_notes()
    if tag:
        notes = [n for n in notes if tag in n.get("tags", [])]
    return {"notes": notes[-limit:], "total": len(notes)}


def search_notes(query: str) -> dict:
    """Search notes by content."""
    notes = _load_notes()
    matches = [n for n in notes if query.lower() in n["content"].lower()]
    return {"matches": matches, "count": len(matches)}


def delete_note(note_id: int) -> dict:
    """Delete a note by ID."""
    notes = _load_notes()
    notes = [n for n in notes if n["id"] != note_id]
    _save_notes(notes)
    return {"status": "deleted", "id": note_id}


# Register tools
register_tool(
    name="add_note",
    description="Save a note for later",
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Note content"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
        },
        "required": ["content"],
    },
    func=add_note,
)

register_tool(
    name="list_notes",
    description="List saved notes",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 20},
            "tag": {"type": "string", "description": "Filter by tag"},
        },
        "required": [],
    },
    func=list_notes,
)

register_tool(
    name="search_notes",
    description="Search notes by content",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search query"}},
        "required": ["query"],
    },
    func=search_notes,
)
