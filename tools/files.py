"""
CORA-GO File Operations
Read, write, list, search, move files
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
import fnmatch


def read_file(path: str, encoding: str = 'utf-8') -> str:
    """Read contents of a file."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"

        content = p.read_text(encoding=encoding)
        return content
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding='latin-1')
        except Exception as e:
            return f"Error reading file: {e}"
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str, encoding: str = 'utf-8') -> str:
    """Write content to a file. Creates parent directories if needed."""
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_files(path: str = '.', pattern: str = '*', recursive: bool = False) -> str:
    """List files in a directory, optionally with pattern matching."""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: Directory not found: {path}"
        if not p.is_dir():
            return f"Error: Not a directory: {path}"

        if recursive:
            files = list(p.rglob(pattern))
        else:
            files = list(p.glob(pattern))

        # Sort: directories first, then files
        dirs = sorted([f for f in files if f.is_dir()])
        regular = sorted([f for f in files if f.is_file()])

        result = []
        for d in dirs:
            result.append(f"[DIR]  {d.name}/")
        for f in regular:
            size = f.stat().st_size
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024}KB"
            else:
                size_str = f"{size // (1024 * 1024)}MB"
            result.append(f"[FILE] {f.name} ({size_str})")

        if not result:
            return f"No files matching '{pattern}' in {path}"

        return f"Contents of {path}:\n" + "\n".join(result)
    except Exception as e:
        return f"Error listing files: {e}"


def search_files(directory: str, pattern: str, content_pattern: Optional[str] = None) -> str:
    """
    Search for files by name pattern, optionally also by content.

    Args:
        directory: Directory to search in
        pattern: Filename pattern (glob style, e.g., "*.py")
        content_pattern: Optional text to search for inside files
    """
    try:
        p = Path(directory).expanduser().resolve()
        if not p.exists():
            return f"Error: Directory not found: {directory}"

        matches = []
        for file in p.rglob(pattern):
            if file.is_file():
                if content_pattern:
                    try:
                        text = file.read_text(encoding='utf-8', errors='ignore')
                        if content_pattern.lower() in text.lower():
                            matches.append(str(file))
                    except:
                        pass
                else:
                    matches.append(str(file))

        if not matches:
            msg = f"No files matching '{pattern}'"
            if content_pattern:
                msg += f" containing '{content_pattern}'"
            return msg + f" in {directory}"

        return f"Found {len(matches)} files:\n" + "\n".join(matches[:50])
    except Exception as e:
        return f"Error searching: {e}"


def move_file(source: str, destination: str) -> str:
    """Move or rename a file/directory."""
    try:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()

        if not src.exists():
            return f"Error: Source not found: {source}"

        # If destination is a directory, move into it
        if dst.is_dir():
            dst = dst / src.name

        # Create parent if needed
        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src), str(dst))
        return f"Moved {source} to {destination}"
    except Exception as e:
        return f"Error moving file: {e}"
