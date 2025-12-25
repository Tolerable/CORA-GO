"""
CORA-GO NAS Tools
Network Attached Storage access.
"""

import subprocess
import platform
from pathlib import Path
from typing import Optional, List
from . import register_tool
from ..config import config


def _is_configured() -> bool:
    """Check if NAS is configured."""
    return bool(config.get("nas.enabled") and config.get("nas.server"))


def _get_share_path(share: str, path: str = "") -> str:
    """Build full UNC path to NAS share."""
    server = config.get("nas.server", "").strip("\\")
    full_path = f"\\\\{server}\\{share}"
    if path:
        full_path += f"\\{path.replace('/', '\\')}"
    return full_path


def check_nas() -> dict:
    """Check NAS connection status."""
    if not _is_configured():
        return {
            "configured": False,
            "error": "NAS not configured",
            "config_needed": ["nas.server", "nas.shares"]
        }

    server = config.get("nas.server")
    shares = config.get("nas.shares", [])

    try:
        # Try to ping the server
        if platform.system() == "Windows":
            result = subprocess.run(
                ["ping", "-n", "1", "-w", "1000", server],
                capture_output=True, text=True, timeout=5
            )
            reachable = result.returncode == 0
        else:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", server],
                capture_output=True, text=True, timeout=5
            )
            reachable = result.returncode == 0

        return {
            "configured": True,
            "server": server,
            "reachable": reachable,
            "shares": shares
        }

    except Exception as e:
        return {"configured": True, "error": str(e)}


def nas_list(share: Optional[str] = None, path: str = "") -> dict:
    """
    List files on NAS.

    Args:
        share: Share name (uses default if not specified)
        path: Path within share

    Returns:
        File listing
    """
    if not _is_configured():
        return {"error": "NAS not configured. Set nas.server in config."}

    if not share:
        share = config.get("nas.default_share", "TEMP")

    shares = config.get("nas.shares", [])
    if share not in shares:
        return {"error": f"Share '{share}' not in configured shares: {shares}"}

    full_path = _get_share_path(share, path)

    try:
        if platform.system() == "Windows":
            cmd = f'Get-ChildItem "{full_path}" | Select-Object Name, Length, LastWriteTime, PSIsContainer | ConvertTo-Json'
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode != 0:
                return {"error": result.stderr or "Failed to list directory"}

            import json
            try:
                items = json.loads(result.stdout)
                if isinstance(items, dict):
                    items = [items]  # Single item

                files = []
                for item in items:
                    files.append({
                        "name": item.get("Name"),
                        "size": item.get("Length"),
                        "is_dir": item.get("PSIsContainer", False),
                        "modified": item.get("LastWriteTime", {}).get("DateTime") if isinstance(item.get("LastWriteTime"), dict) else str(item.get("LastWriteTime"))
                    })
                return {"path": full_path, "files": files}
            except json.JSONDecodeError:
                return {"path": full_path, "raw": result.stdout}
        else:
            # Linux/Mac - mount point or smbclient
            return {"error": "NAS listing on non-Windows requires mounted share"}

    except subprocess.TimeoutExpired:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": str(e)}


def nas_read(share: str, filepath: str) -> dict:
    """
    Read a text file from NAS.

    Args:
        share: Share name
        filepath: Path to file within share

    Returns:
        File contents
    """
    if not _is_configured():
        return {"error": "NAS not configured"}

    full_path = _get_share_path(share, filepath)

    try:
        if platform.system() == "Windows":
            cmd = f'Get-Content "{full_path}" -Raw'
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return {"error": result.stderr or "Failed to read file"}

            return {"path": full_path, "content": result.stdout, "size": len(result.stdout)}
        else:
            return {"error": "NAS read on non-Windows requires mounted share"}

    except subprocess.TimeoutExpired:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": str(e)}


def nas_write(share: str, filepath: str, content: str) -> dict:
    """
    Write content to a file on NAS.

    Args:
        share: Share name
        filepath: Path to file within share
        content: Content to write

    Returns:
        Status dict
    """
    if not _is_configured():
        return {"error": "NAS not configured"}

    full_path = _get_share_path(share, filepath)

    try:
        if platform.system() == "Windows":
            import tempfile
            import os

            # Write to temp file first, then copy
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name

            cmd = f'Copy-Item "{temp_path}" "{full_path}" -Force'
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=30
            )
            os.unlink(temp_path)

            if result.returncode != 0:
                return {"error": result.stderr or "Failed to write file"}

            return {"status": "ok", "path": full_path, "size": len(content)}
        else:
            return {"error": "NAS write on non-Windows requires mounted share"}

    except Exception as e:
        return {"error": str(e)}


def nas_copy(local_path: str, share: Optional[str] = None, dest_path: str = "") -> dict:
    """
    Copy local file/folder to NAS.

    Args:
        local_path: Local file or folder path
        share: Destination share (default from config)
        dest_path: Destination path within share

    Returns:
        Status dict
    """
    if not _is_configured():
        return {"error": "NAS not configured"}

    if not share:
        share = config.get("nas.default_share", "BACKUPS")

    local = Path(local_path)
    if not local.exists():
        return {"error": f"Local path not found: {local_path}"}

    nas_dest = _get_share_path(share, dest_path)

    try:
        if platform.system() == "Windows":
            if local.is_dir():
                # Use robocopy for folders
                cmd = f'robocopy "{local_path}" "{nas_dest}" /E /R:1 /W:1 /MT:8'
                result = subprocess.run(
                    ["cmd", "/c", cmd],
                    capture_output=True, text=True, timeout=300
                )
                # Robocopy returns 0-7 for success
                if result.returncode <= 7:
                    return {"status": "ok", "type": "folder", "destination": nas_dest}
                return {"error": result.stderr or result.stdout}
            else:
                # Use Copy-Item for files
                cmd = f'Copy-Item "{local_path}" "{nas_dest}" -Force'
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode != 0:
                    return {"error": result.stderr or "Copy failed"}
                return {"status": "ok", "type": "file", "destination": nas_dest}
        else:
            return {"error": "NAS copy on non-Windows requires mounted share"}

    except subprocess.TimeoutExpired:
        return {"error": "Copy timed out"}
    except Exception as e:
        return {"error": str(e)}


def nas_delete(share: str, filepath: str) -> dict:
    """
    Delete a file from NAS.

    Args:
        share: Share name
        filepath: Path to file within share

    Returns:
        Status dict
    """
    if not _is_configured():
        return {"error": "NAS not configured"}

    full_path = _get_share_path(share, filepath)

    try:
        if platform.system() == "Windows":
            cmd = f'Remove-Item "{full_path}" -Force'
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return {"error": result.stderr or "Delete failed"}

            return {"status": "deleted", "path": full_path}
        else:
            return {"error": "NAS delete on non-Windows requires mounted share"}

    except Exception as e:
        return {"error": str(e)}


# Register tools
register_tool(
    name="check_nas",
    description="Check NAS connection status",
    parameters={"type": "object", "properties": {}, "required": []},
    func=check_nas,
)

register_tool(
    name="nas_list",
    description="List files on NAS share",
    parameters={
        "type": "object",
        "properties": {
            "share": {"type": "string", "description": "Share name (TEMP, BACKUPS, MUSIC, etc.)"},
            "path": {"type": "string", "description": "Path within share", "default": ""},
        },
        "required": [],
    },
    func=nas_list,
)

register_tool(
    name="nas_read",
    description="Read a text file from NAS",
    parameters={
        "type": "object",
        "properties": {
            "share": {"type": "string", "description": "Share name"},
            "filepath": {"type": "string", "description": "Path to file"},
        },
        "required": ["share", "filepath"],
    },
    func=nas_read,
)

register_tool(
    name="nas_write",
    description="Write content to a file on NAS",
    parameters={
        "type": "object",
        "properties": {
            "share": {"type": "string", "description": "Share name"},
            "filepath": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["share", "filepath", "content"],
    },
    func=nas_write,
)

register_tool(
    name="nas_copy",
    description="Copy local file/folder to NAS",
    parameters={
        "type": "object",
        "properties": {
            "local_path": {"type": "string", "description": "Local file/folder path"},
            "share": {"type": "string", "description": "Destination share"},
            "dest_path": {"type": "string", "description": "Destination path in share", "default": ""},
        },
        "required": ["local_path"],
    },
    func=nas_copy,
)

register_tool(
    name="nas_delete",
    description="Delete a file from NAS",
    parameters={
        "type": "object",
        "properties": {
            "share": {"type": "string", "description": "Share name"},
            "filepath": {"type": "string", "description": "Path to file"},
        },
        "required": ["share", "filepath"],
    },
    func=nas_delete,
)
