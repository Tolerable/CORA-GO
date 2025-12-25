"""
CORA-GO System Operations
Shell commands, system info, screenshots, clipboard
"""

import os
import sys
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional


# Safety: blocked commands
BLOCKED_COMMANDS = [
    'rm -rf /', 'rm -r /', 'format c:', 'del /f /s /q',
    'shutdown', 'mkfs', ':(){', 'dd if=/dev/zero',
    'drop database', 'drop table', 'truncate table'
]


def run_shell(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    """
    Run a shell command and return output.

    Args:
        command: Command to run
        timeout: Max execution time in seconds
        cwd: Working directory (optional)
    """
    # Safety check
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"Error: Blocked command detected: {blocked}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )

        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"

        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"

        return output.strip() if output.strip() else "(No output)"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as e:
        return f"Error running command: {e}"


def system_info() -> str:
    """Get system information."""
    try:
        info = []
        info.append(f"Platform: {platform.system()} {platform.release()}")
        info.append(f"Machine: {platform.machine()}")
        info.append(f"Processor: {platform.processor()}")
        info.append(f"Python: {platform.python_version()}")
        info.append(f"User: {os.getenv('USERNAME') or os.getenv('USER')}")
        info.append(f"Home: {Path.home()}")
        info.append(f"CWD: {os.getcwd()}")
        info.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Check for Ollama
        try:
            result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info.append(f"Ollama: {result.stdout.strip()}")
        except:
            info.append("Ollama: Not installed")

        return "\n".join(info)
    except Exception as e:
        return f"Error getting system info: {e}"


def take_screenshot(name: str = "", output_dir: Optional[str] = None) -> str:
    """Take a screenshot and save it."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png" if name else f"screenshot_{timestamp}.png"

        if output_dir:
            filepath = Path(output_dir) / filename
        else:
            filepath = Path.home() / "Pictures" / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)

        if os.name == 'nt':
            # Windows: use PowerShell
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
            $bitmap.Save("{filepath}")
            $graphics.Dispose()
            $bitmap.Dispose()
            '''
            subprocess.run(['powershell', '-Command', ps_script], capture_output=True, timeout=10)
        else:
            # Linux/Mac: try scrot or screencapture
            if platform.system() == 'Darwin':
                subprocess.run(['screencapture', str(filepath)], timeout=10)
            else:
                subprocess.run(['scrot', str(filepath)], timeout=10)

        if filepath.exists():
            return f"Screenshot saved: {filepath}"
        return "Screenshot failed - file not created"
    except Exception as e:
        return f"Screenshot error: {e}"


def get_clipboard() -> str:
    """Get clipboard contents."""
    try:
        if os.name == 'nt':
            result = subprocess.run(
                ['powershell', '-Command', 'Get-Clipboard'],
                capture_output=True, text=True, timeout=5
            )
            text = result.stdout.strip()
            if text:
                return f"Clipboard ({len(text)} chars):\n{text[:1000]}"
            return "Clipboard is empty"
        else:
            # Try xclip on Linux
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() or "Clipboard is empty"
    except Exception as e:
        return f"Clipboard error: {e}"


def set_clipboard(text: str) -> str:
    """Copy text to clipboard."""
    try:
        if os.name == 'nt':
            # Escape for PowerShell
            escaped = text.replace('`', '``').replace('"', '`"').replace('\n', '`n')
            subprocess.run(
                ['powershell', '-Command', f'Set-Clipboard -Value "{escaped}"'],
                capture_output=True, timeout=5
            )
            return f"Copied {len(text)} chars to clipboard"
        else:
            # Try xclip on Linux
            proc = subprocess.Popen(
                ['xclip', '-selection', 'clipboard'],
                stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode())
            return f"Copied {len(text)} chars to clipboard"
    except Exception as e:
        return f"Clipboard error: {e}"
