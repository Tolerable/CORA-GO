"""
CORA-GO Bot Management
Launch, stop, and manage bot daemons
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Optional


# Bot directory locations to search
BOT_SEARCH_PATHS = [
    Path.home() / ".cora-go" / "bots",
    Path("C:/claude"),  # Windows default
    Path.home() / "bots",
]

# Track running bots
_running_bots: Dict[str, subprocess.Popen] = {}


def _find_bot_folders() -> Dict[str, Path]:
    """Find all valid bot folders."""
    bots = {}

    for search_path in BOT_SEARCH_PATHS:
        if not search_path.exists():
            continue

        for item in search_path.iterdir():
            if not item.is_dir():
                continue

            # Check for bot indicators
            has_start = (item / 'start.bat').exists() or (item / 'start.sh').exists()
            has_config = (item / 'settings.json').exists() or (item / 'configbot.json').exists()
            has_claude = (item / 'CLAUDE.md').exists()
            has_main = (item / 'main.py').exists() or (item / 'bot.py').exists()

            if has_start or has_config or has_claude or has_main:
                bots[item.name] = item

    return bots


def list_bots() -> str:
    """List available bot folders that can be launched."""
    bots = _find_bot_folders()

    if not bots:
        return "No bot folders found. Expected locations:\n" + \
               "\n".join(f"  - {p}" for p in BOT_SEARCH_PATHS)

    result = ["Available bots:"]
    for name, path in sorted(bots.items()):
        is_running = name in _running_bots and _running_bots[name].poll() is None
        status = " [RUNNING]" if is_running else ""

        # Detect bot type
        bot_type = "unknown"
        if (path / 'start.bat').exists():
            bot_type = "bat launcher"
        elif (path / 'main.py').exists():
            bot_type = "python"
        elif (path / 'CLAUDE.md').exists():
            bot_type = "claude config"

        result.append(f"  {name}{status} ({bot_type})")

    return "\n".join(result)


def launch_bot(
    name: str,
    mode: str = "cli",
    args: Optional[str] = None
) -> str:
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
        return f"{name} already running (PID: {_running_bots[name].pid})"

    # Find bot folder
    bots = _find_bot_folders()
    if name not in bots:
        return f"Bot '{name}' not found. Use list_bots() to see available bots."

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
            return f"Launched {name} via start.bat (PID: {proc.pid})"

        if os.name != 'nt' and start_sh.exists():
            proc = subprocess.Popen(
                ['bash', str(start_sh)],
                cwd=str(bot_dir)
            )
            _running_bots[name] = proc
            return f"Launched {name} via start.sh (PID: {proc.pid})"

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
            return f"Launched {name} (PID: {proc.pid})"

        # 3. Try minibot with this folder as home
        minibot_locations = [
            Path("C:/claude/minibot-package/minibot.py"),
            Path.home() / ".cora-go" / "minibot.py"
        ]

        for minibot in minibot_locations:
            if minibot.exists():
                cmd = ['py', '-3.12', str(minibot), '--home', str(bot_dir)]
                if mode == 'gui':
                    cmd.append('--gui')

                if os.name == 'nt':
                    proc = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    proc = subprocess.Popen(cmd)

                _running_bots[name] = proc
                return f"Launched {name} via minibot (PID: {proc.pid})"

        return f"No launch method found for {name}"

    except Exception as e:
        return f"Error launching {name}: {e}"


def stop_bot(name: str) -> str:
    """
    Stop a running bot.

    Args:
        name: Bot name to stop
    """
    global _running_bots

    if name not in _running_bots:
        return f"{name} not in running bots list"

    proc = _running_bots[name]

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except:
            proc.kill()

        del _running_bots[name]
        return f"Stopped {name}"

    del _running_bots[name]
    return f"{name} was already stopped"


def running_bots() -> str:
    """List currently running bots."""
    global _running_bots

    active = []
    to_remove = []

    for name, proc in _running_bots.items():
        if proc.poll() is None:
            active.append(f"  {name} (PID: {proc.pid})")
        else:
            to_remove.append(name)

    # Clean up dead processes
    for name in to_remove:
        del _running_bots[name]

    if not active:
        return "No bots currently running"

    return "Running bots:\n" + "\n".join(active)


def stop_all_bots() -> str:
    """Stop all running bots."""
    global _running_bots

    if not _running_bots:
        return "No bots running"

    stopped = []
    for name in list(_running_bots.keys()):
        result = stop_bot(name)
        stopped.append(f"  {name}: {result}")

    return "Stopped bots:\n" + "\n".join(stopped)
