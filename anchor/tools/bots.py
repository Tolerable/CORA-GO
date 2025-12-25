"""
CORA-GO Bot Management
Launch, stop, and manage bot daemons from mobile.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from . import register_tool
from ..config import config


# Track running bots
_running_bots: Dict[str, subprocess.Popen] = {}


def _get_bot_search_paths() -> List[Path]:
    """Get configured bot search paths."""
    default_paths = [
        Path("C:/claude"),
        Path.home() / ".cora-go" / "bots",
        Path.home() / "bots",
    ]

    # Add any custom paths from config
    custom = config.get("bots.search_paths", [])
    for p in custom:
        default_paths.insert(0, Path(p))

    return default_paths


def _find_bot_folders() -> Dict[str, Path]:
    """Find all valid bot folders."""
    bots = {}

    for search_path in _get_bot_search_paths():
        if not search_path.exists():
            continue

        for item in search_path.iterdir():
            if not item.is_dir():
                continue

            # Skip common non-bot folders
            if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules', 'venv']:
                continue

            # Check for bot indicators
            has_start = (item / 'start.bat').exists() or (item / 'start.sh').exists()
            has_config = (item / 'settings.json').exists() or (item / 'configbot.json').exists()
            has_claude = (item / 'CLAUDE.md').exists()
            has_main = (item / 'main.py').exists() or (item / 'bot.py').exists()

            if has_start or has_config or has_claude or has_main:
                bots[item.name] = item

    return bots


def list_bots() -> dict:
    """List available bot folders that can be launched."""
    bots = _find_bot_folders()

    if not bots:
        return {
            "bots": [],
            "search_paths": [str(p) for p in _get_bot_search_paths()],
            "message": "No bot folders found"
        }

    bot_list = []
    for name, path in sorted(bots.items()):
        is_running = name in _running_bots and _running_bots[name].poll() is None

        # Detect bot type
        bot_type = "unknown"
        if (path / 'start.bat').exists():
            bot_type = "bat"
        elif (path / 'main.py').exists():
            bot_type = "python"
        elif (path / 'CLAUDE.md').exists():
            bot_type = "claude"

        bot_list.append({
            "name": name,
            "path": str(path),
            "type": bot_type,
            "running": is_running,
            "pid": _running_bots[name].pid if is_running else None
        })

    return {"bots": bot_list, "count": len(bot_list)}


def launch_bot(name: str, mode: str = "cli", args: Optional[str] = None) -> dict:
    """
    Launch a bot daemon.

    Args:
        name: Bot folder name
        mode: Launch mode (cli, gui, service)
        args: Additional arguments to pass
    """
    global _running_bots

    # Check if already running
    if name in _running_bots and _running_bots[name].poll() is None:
        return {
            "success": False,
            "error": f"{name} already running",
            "pid": _running_bots[name].pid
        }

    # Find bot folder
    bots = _find_bot_folders()
    if name not in bots:
        return {
            "success": False,
            "error": f"Bot '{name}' not found",
            "available": list(bots.keys())
        }

    bot_dir = bots[name]

    try:
        # Try different launch methods

        # 1. Start script (bat/sh)
        start_bat = bot_dir / 'start.bat'
        start_sh = bot_dir / 'start.sh'

        if os.name == 'nt' and start_bat.exists():
            proc = subprocess.Popen(
                ['cmd', '/c', str(start_bat)],
                cwd=str(bot_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            _running_bots[name] = proc
            return {"success": True, "method": "start.bat", "pid": proc.pid}

        if os.name != 'nt' and start_sh.exists():
            proc = subprocess.Popen(
                ['bash', str(start_sh)],
                cwd=str(bot_dir)
            )
            _running_bots[name] = proc
            return {"success": True, "method": "start.sh", "pid": proc.pid}

        # 2. Main Python script
        main_py = bot_dir / 'main.py'
        bot_py = bot_dir / 'bot.py'
        entry = main_py if main_py.exists() else (bot_py if bot_py.exists() else None)

        if entry:
            cmd = ['py', '-3.12', str(entry)]
            if mode == 'gui':
                cmd.append('--gui')
            if args:
                cmd.extend(args.split())

            if os.name == 'nt':
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(bot_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                proc = subprocess.Popen(cmd, cwd=str(bot_dir))

            _running_bots[name] = proc
            return {"success": True, "method": "python", "pid": proc.pid}

        # 3. Try Claude CLI with this folder
        if (bot_dir / 'CLAUDE.md').exists():
            cmd = ['claude', '-p', f'Run startup for {name}']

            if os.name == 'nt':
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(bot_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                proc = subprocess.Popen(cmd, cwd=str(bot_dir))

            _running_bots[name] = proc
            return {"success": True, "method": "claude-cli", "pid": proc.pid}

        return {"success": False, "error": f"No launch method found for {name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def stop_bot(name: str) -> dict:
    """
    Stop a running bot.

    Args:
        name: Bot name to stop
    """
    global _running_bots

    if name not in _running_bots:
        return {"success": False, "error": f"{name} not in running bots list"}

    proc = _running_bots[name]

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()

        del _running_bots[name]
        return {"success": True, "message": f"Stopped {name}"}

    del _running_bots[name]
    return {"success": True, "message": f"{name} was already stopped"}


def running_bots() -> dict:
    """List currently running bots."""
    global _running_bots

    active = []
    to_remove = []

    for name, proc in _running_bots.items():
        if proc.poll() is None:
            active.append({"name": name, "pid": proc.pid})
        else:
            to_remove.append(name)

    # Clean up dead processes
    for name in to_remove:
        del _running_bots[name]

    return {"running": active, "count": len(active)}


def stop_all_bots() -> dict:
    """Stop all running bots."""
    global _running_bots

    if not _running_bots:
        return {"success": True, "message": "No bots running", "stopped": []}

    stopped = []
    for name in list(_running_bots.keys()):
        result = stop_bot(name)
        stopped.append({"name": name, "result": result})

    return {"success": True, "stopped": stopped}


# Register tools
register_tool(
    name="list_bots",
    description="List available bot folders that can be launched",
    parameters={"type": "object", "properties": {}, "required": []},
    func=list_bots,
)

register_tool(
    name="launch_bot",
    description="Launch a bot daemon by name",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Bot folder name"},
            "mode": {"type": "string", "enum": ["cli", "gui"], "default": "cli"},
            "args": {"type": "string", "description": "Additional arguments"},
        },
        "required": ["name"],
    },
    func=launch_bot,
)

register_tool(
    name="stop_bot",
    description="Stop a running bot",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Bot name to stop"},
        },
        "required": ["name"],
    },
    func=stop_bot,
)

register_tool(
    name="running_bots",
    description="List currently running bots",
    parameters={"type": "object", "properties": {}, "required": []},
    func=running_bots,
)

register_tool(
    name="stop_all_bots",
    description="Stop all running bots",
    parameters={"type": "object", "properties": {}, "required": []},
    func=stop_all_bots,
)
