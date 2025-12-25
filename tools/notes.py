"""
CORA-GO Notes/Knowledge Base
Persistent storage for notes and knowledge
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


# Default notes location
NOTES_DIR = Path.home() / ".cora-go"
NOTES_FILE = NOTES_DIR / "notes.json"


def _ensure_notes_file() -> Path:
    """Ensure notes directory and file exist."""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTES_FILE.exists():
        NOTES_FILE.write_text('{}')
    return NOTES_FILE


def _load_notes() -> Dict[str, Any]:
    """Load all notes from file."""
    try:
        _ensure_notes_file()
        return json.loads(NOTES_FILE.read_text())
    except:
        return {}


def _save_notes(notes: Dict[str, Any]) -> None:
    """Save all notes to file."""
    _ensure_notes_file()
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


def add_note(key: str, content: str, tags: Optional[str] = None) -> str:
    """
    Add or update a note.

    Args:
        key: Unique identifier for the note
        content: Note content
        tags: Comma-separated tags (optional)
    """
    try:
        notes = _load_notes()

        note = {
            "content": content,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()
        }

        if tags:
            note["tags"] = [t.strip() for t in tags.split(",")]

        # If updating existing note, keep original created date
        if key in notes:
            note["created"] = notes[key].get("created", note["created"])

        notes[key] = note
        _save_notes(notes)

        return f"Note '{key}' saved"
    except Exception as e:
        return f"Error saving note: {e}"


def get_note(key: str) -> str:
    """
    Get a specific note by key.

    Args:
        key: Note identifier
    """
    try:
        notes = _load_notes()

        if key not in notes:
            return f"Note '{key}' not found"

        note = notes[key]
        result = [f"Note: {key}"]
        result.append(f"Content: {note['content']}")

        if note.get('tags'):
            result.append(f"Tags: {', '.join(note['tags'])}")

        result.append(f"Updated: {note.get('updated', 'Unknown')}")

        return "\n".join(result)
    except Exception as e:
        return f"Error getting note: {e}"


def list_notes(tag: Optional[str] = None) -> str:
    """
    List all notes, optionally filtered by tag.

    Args:
        tag: Filter by this tag (optional)
    """
    try:
        notes = _load_notes()

        if not notes:
            return "No notes saved"

        filtered = []
        for key, note in notes.items():
            if tag:
                note_tags = note.get('tags', [])
                if tag.lower() not in [t.lower() for t in note_tags]:
                    continue

            preview = note['content'][:50]
            if len(note['content']) > 50:
                preview += "..."

            tags_str = ""
            if note.get('tags'):
                tags_str = f" [{', '.join(note['tags'])}]"

            filtered.append(f"  {key}: {preview}{tags_str}")

        if not filtered:
            if tag:
                return f"No notes with tag '{tag}'"
            return "No notes saved"

        header = f"Notes ({len(filtered)})"
        if tag:
            header += f" with tag '{tag}'"

        return header + ":\n" + "\n".join(filtered)
    except Exception as e:
        return f"Error listing notes: {e}"


def delete_note(key: str) -> str:
    """
    Delete a note.

    Args:
        key: Note identifier to delete
    """
    try:
        notes = _load_notes()

        if key not in notes:
            return f"Note '{key}' not found"

        del notes[key]
        _save_notes(notes)

        return f"Note '{key}' deleted"
    except Exception as e:
        return f"Error deleting note: {e}"


def search_notes(query: str) -> str:
    """
    Search notes by content.

    Args:
        query: Text to search for
    """
    try:
        notes = _load_notes()

        if not notes:
            return "No notes saved"

        matches = []
        query_lower = query.lower()

        for key, note in notes.items():
            content = note.get('content', '').lower()
            tags = ' '.join(note.get('tags', [])).lower()

            if query_lower in content or query_lower in tags or query_lower in key.lower():
                preview = note['content'][:50]
                if len(note['content']) > 50:
                    preview += "..."
                matches.append(f"  {key}: {preview}")

        if not matches:
            return f"No notes matching '{query}'"

        return f"Notes matching '{query}' ({len(matches)}):\n" + "\n".join(matches)
    except Exception as e:
        return f"Error searching notes: {e}"
