"""
CORA-GO File Tools
Safe file operations with path validation.
"""

import os
from pathlib import Path
from typing import Optional, List
from . import register_tool


def _validate_path(path: str) -> Path:
    """Validate path is safe (no traversal attacks)."""
    p = Path(path).resolve()
    # Block obvious dangerous paths
    blocked = ["C:\\Windows\\System32", "/etc", "/bin", "/usr"]
    for b in blocked:
        if str(p).startswith(b):
            raise ValueError(f"Access denied: {b}")
    return p


def read_file(path: str, max_lines: int = 200) -> dict:
    """Read file contents."""
    try:
        p = _validate_path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if p.stat().st_size > 500000:  # 500KB limit
            return {"error": "File too large"}
        
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()[:max_lines]
        
        return {
            "path": str(p),
            "lines": len(lines),
            "content": "".join(lines),
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write content to file."""
    try:
        p = _validate_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "written", "path": str(p), "bytes": len(content)}
    except Exception as e:
        return {"error": str(e)}


def list_files(path: str = ".", pattern: str = "*") -> dict:
    """List files in directory."""
    try:
        p = _validate_path(path)
        if not p.is_dir():
            return {"error": "Not a directory"}
        
        files = []
        for f in p.glob(pattern):
            files.append({
                "name": f.name,
                "is_dir": f.is_dir(),
                "size": f.stat().st_size if f.is_file() else 0,
            })
        
        return {"path": str(p), "files": files[:100]}
    except Exception as e:
        return {"error": str(e)}


def search_files(path: str, pattern: str, content: Optional[str] = None) -> dict:
    """Search for files, optionally by content."""
    try:
        p = _validate_path(path)
        matches = []
        
        for f in p.rglob(pattern):
            if len(matches) >= 50:
                break
            if f.is_file():
                if content:
                    try:
                        text = f.read_text(encoding='utf-8', errors='ignore')[:10000]
                        if content.lower() in text.lower():
                            matches.append(str(f))
                    except Exception:
                        pass
                else:
                    matches.append(str(f))
        
        return {"matches": matches, "count": len(matches)}
    except Exception as e:
        return {"error": str(e)}


# Register tools
register_tool(
    name="read_file",
    description="Read contents of a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "max_lines": {"type": "integer", "description": "Max lines to read", "default": 200},
        },
        "required": ["path"],
    },
    func=read_file,
)

register_tool(
    name="write_file",
    description="Write content to a file",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
    func=write_file,
)

register_tool(
    name="list_files",
    description="List files in a directory",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path", "default": "."},
            "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
        },
        "required": [],
    },
    func=list_files,
)
