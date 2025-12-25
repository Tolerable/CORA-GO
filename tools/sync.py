"""
CORA-GO Sync Module
Windows <-> Supabase <-> Mobile sync
Like Claude Colab - desktop agent talks to cloud, mobile queries it
"""

import json
import urllib.request
import urllib.parse
import os
import platform
import socket
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


# Config location
CONFIG_DIR = Path.home() / ".cora-go"
SYNC_CONFIG = CONFIG_DIR / "sync_config.json"
DEVICE_ID_FILE = CONFIG_DIR / "device_id"


# Default Supabase (user sets their own)
DEFAULT_CONFIG = {
    "supabase_url": "",
    "supabase_anon_key": "",
    "user_token": "",  # JWT from auth
    "device_name": platform.node(),
    "sync_enabled": False,
    "sync_interval_seconds": 60,
    "auto_sync_notes": True,
    "auto_sync_incidents": True
}


def _ensure_config():
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> Dict[str, Any]:
    """Load sync config."""
    _ensure_config()
    if SYNC_CONFIG.exists():
        try:
            saved = json.loads(SYNC_CONFIG.read_text())
            return {**DEFAULT_CONFIG, **saved}
        except:
            pass
    return DEFAULT_CONFIG.copy()


def _save_config(config: Dict[str, Any]):
    """Save sync config."""
    _ensure_config()
    SYNC_CONFIG.write_text(json.dumps(config, indent=2))


def _get_device_id() -> str:
    """Get or create persistent device ID."""
    _ensure_config()
    if DEVICE_ID_FILE.exists():
        return DEVICE_ID_FILE.read_text().strip()

    import uuid
    device_id = str(uuid.uuid4())
    DEVICE_ID_FILE.write_text(device_id)
    return device_id


def _supabase_request(
    endpoint: str,
    method: str = "POST",
    data: Optional[Dict] = None,
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make authenticated request to Supabase."""
    config = config or _load_config()

    if not config.get("supabase_url") or not config.get("supabase_anon_key"):
        return {"success": False, "error": "Supabase not configured"}

    url = f"{config['supabase_url']}/rest/v1/rpc/{endpoint}"

    headers = {
        "apikey": config["supabase_anon_key"],
        "Authorization": f"Bearer {config.get('user_token') or config['supabase_anon_key']}",
        "Content-Type": "application/json"
    }

    try:
        body = json.dumps(data or {}).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def configure_sync(
    supabase_url: str,
    anon_key: str,
    user_token: Optional[str] = None
) -> str:
    """
    Configure Supabase sync settings.

    Args:
        supabase_url: Your Supabase project URL
        anon_key: Supabase anon key
        user_token: JWT from user login (optional)
    """
    config = _load_config()
    config["supabase_url"] = supabase_url.rstrip("/")
    config["supabase_anon_key"] = anon_key
    if user_token:
        config["user_token"] = user_token
    config["sync_enabled"] = True
    _save_config(config)

    return "Sync configured. Run sync_status() to verify connection."


def sync_status() -> str:
    """Check sync configuration and connection status."""
    config = _load_config()

    lines = ["CORA-GO Sync Status", "=" * 40]

    if not config.get("supabase_url"):
        lines.append("Status: NOT CONFIGURED")
        lines.append("Run configure_sync() to set up")
        return "\n".join(lines)

    lines.append(f"Supabase: {config['supabase_url'][:50]}...")
    lines.append(f"Device: {config.get('device_name', 'Unknown')}")
    lines.append(f"Device ID: {_get_device_id()[:8]}...")
    lines.append(f"Sync Enabled: {config.get('sync_enabled', False)}")

    # Test connection
    try:
        result = _supabase_request("get_my_profile", config=config)
        if result.get("success"):
            profile = result.get("profile", {})
            lines.append(f"Connected as: {profile.get('username', 'Unknown')}")
            lines.append("Connection: OK")
        else:
            lines.append(f"Connection: FAILED - {result.get('error', 'Unknown')}")
    except Exception as e:
        lines.append(f"Connection: ERROR - {e}")

    return "\n".join(lines)


def get_system_report() -> Dict[str, Any]:
    """Generate system report for sync."""

    report = {
        "device_id": _get_device_id(),
        "device_name": platform.node(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "hostname": socket.gethostname(),
        "timestamp": datetime.now().isoformat()
    }

    # Try to get more system info
    try:
        import psutil
        report["cpu_percent"] = psutil.cpu_percent(interval=1)
        report["memory_percent"] = psutil.virtual_memory().percent
        report["disk_percent"] = psutil.disk_usage('/').percent
        report["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).isoformat()
    except ImportError:
        report["system_details"] = "psutil not installed"

    return report


def sync_notes_up() -> str:
    """Sync local notes to Supabase."""
    from .notes import _load_notes

    config = _load_config()
    if not config.get("sync_enabled"):
        return "Sync not enabled"

    notes = _load_notes()
    if not notes:
        return "No local notes to sync"

    synced = 0
    errors = []

    for key, note in notes.items():
        result = _supabase_request("upsert_note", data={
            "p_key": key,
            "p_content": note.get("content", ""),
            "p_tags": note.get("tags", [])
        }, config=config)

        if result.get("success"):
            synced += 1
        else:
            errors.append(f"{key}: {result.get('error', 'Unknown')}")

    if errors:
        return f"Synced {synced} notes, {len(errors)} errors:\n" + "\n".join(errors[:5])
    return f"Synced {synced} notes to cloud"


def sync_notes_down() -> str:
    """Download notes from Supabase to local."""
    from .notes import _save_notes, _load_notes

    config = _load_config()
    if not config.get("sync_enabled"):
        return "Sync not enabled"

    result = _supabase_request("search_notes", data={}, config=config)

    if not result.get("success"):
        return f"Sync failed: {result.get('error', 'Unknown')}"

    cloud_notes = result.get("notes", [])
    if not cloud_notes:
        return "No cloud notes to sync"

    local_notes = _load_notes()

    for note in cloud_notes:
        key = note.get("key")
        local_notes[key] = {
            "content": note.get("content", ""),
            "tags": note.get("tags", []),
            "created": note.get("created_at"),
            "updated": note.get("updated_at")
        }

    _save_notes(local_notes)
    return f"Downloaded {len(cloud_notes)} notes from cloud"


def sync_incident(
    category: str,
    transcript: Optional[str] = None,
    duration: Optional[float] = None,
    metadata: Optional[Dict] = None
) -> str:
    """Sync an incident to Supabase."""
    config = _load_config()
    if not config.get("sync_enabled"):
        return "Sync not enabled (incident saved locally only)"

    result = _supabase_request("log_incident", data={
        "p_category": category,
        "p_transcript": transcript,
        "p_duration": duration,
        "p_metadata": json.dumps(metadata or {})
    }, config=config)

    if result.get("success"):
        return "Incident synced to cloud"
    return f"Sync failed: {result.get('error', 'Unknown')}"


def register_device() -> str:
    """Register this device with Supabase for remote control."""
    config = _load_config()
    if not config.get("sync_enabled"):
        return "Sync not enabled"

    report = get_system_report()

    result = _supabase_request("register_device", data={
        "p_device_name": report["device_name"],
        "p_device_type": f"{report['platform']} Desktop",
        "p_push_token": None  # Desktop doesn't have push
    }, config=config)

    if result.get("success"):
        return f"Device registered: {report['device_name']}"
    return f"Registration failed: {result.get('error', 'Unknown')}"


def heartbeat() -> str:
    """Send heartbeat to cloud (for presence tracking)."""
    config = _load_config()
    if not config.get("sync_enabled"):
        return "Sync not enabled"

    device_id = _get_device_id()

    result = _supabase_request("device_heartbeat", data={
        "p_device_id": device_id
    }, config=config)

    if result.get("success"):
        return "Heartbeat sent"
    return f"Heartbeat failed: {result.get('error', 'Unknown')}"


def push_system_status() -> str:
    """Push system status to cloud for mobile monitoring."""
    config = _load_config()
    if not config.get("sync_enabled"):
        return "Sync not enabled"

    report = get_system_report()

    # Store as a note with special key
    result = _supabase_request("upsert_note", data={
        "p_key": f"_system_status_{_get_device_id()[:8]}",
        "p_content": json.dumps(report, indent=2),
        "p_tags": ["system", "status", "auto"]
    }, config=config)

    if result.get("success"):
        return "System status pushed to cloud"
    return f"Push failed: {result.get('error', 'Unknown')}"


def run_sync_loop(interval_seconds: int = 60):
    """
    Run continuous sync loop.

    Args:
        interval_seconds: How often to sync (default 60s)
    """
    import time

    print(f"Starting sync loop (every {interval_seconds}s)")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Syncing...")

            # Heartbeat
            heartbeat()

            # Push system status
            push_system_status()

            # Sync notes (bidirectional)
            sync_notes_up()

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sync complete")

        except KeyboardInterrupt:
            print("\nSync loop stopped")
            break
        except Exception as e:
            print(f"Sync error: {e}")

        time.sleep(interval_seconds)
