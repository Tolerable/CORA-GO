"""
CORA-GO System Tools
System info, processes, clipboard, screenshots.
"""

import platform
import subprocess
import shutil
from datetime import datetime
from typing import Optional
from . import register_tool


def get_time() -> dict:
    """Get current date and time."""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "iso": now.isoformat(),
    }


def system_info() -> dict:
    """Get system information."""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "hostname": platform.node(),
    }
    
    # Disk space
    try:
        usage = shutil.disk_usage("C:" if platform.system() == "Windows" else "/")
        info["disk_free_gb"] = round(usage.free / (1024**3), 1)
        info["disk_total_gb"] = round(usage.total / (1024**3), 1)
    except Exception:
        pass
    
    # CPU/RAM via psutil if available
    try:
        import psutil
        info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        info["ram_percent"] = psutil.virtual_memory().percent
        info["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 1)
    except ImportError:
        pass
    
    # GPU via nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.free,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 3:
                info["gpu"] = parts[0]
                info["gpu_free_mb"] = int(parts[1])
                info["gpu_total_mb"] = int(parts[2])
    except Exception:
        pass
    
    return info


def get_clipboard() -> dict:
    """Get clipboard contents."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5
            )
            return {"content": result.stdout.strip()[:2000]}
        else:
            # macOS/Linux
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=5
            )
            return {"content": result.stdout.strip()[:2000]}
    except Exception as e:
        return {"error": str(e)}


def set_clipboard(text: str) -> dict:
    """Set clipboard contents."""
    try:
        if platform.system() == "Windows":
            # PowerShell with proper escaping
            safe = text.replace('"', '`"')[:5000]
            subprocess.run(
                ["powershell", "-Command", f'Set-Clipboard -Value "{safe}"'],
                capture_output=True, timeout=5
            )
            return {"status": "copied", "length": len(text)}
        else:
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                   stdin=subprocess.PIPE)
            proc.communicate(text.encode())
            return {"status": "copied", "length": len(text)}
    except Exception as e:
        return {"error": str(e)}


def list_processes(filter: Optional[str] = None) -> dict:
    """List running processes."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")[:50]  # Limit
            procs = []
            for line in lines:
                parts = line.strip('"').split('","')
                if len(parts) >= 2:
                    name = parts[0]
                    if filter and filter.lower() not in name.lower():
                        continue
                    procs.append({"name": name, "pid": parts[1] if len(parts) > 1 else ""})
            return {"processes": procs[:20]}
        else:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
            return {"raw": result.stdout[:3000]}
    except Exception as e:
        return {"error": str(e)}


def kill_process(name: str) -> dict:
    """Kill process by name (requires confirmation)."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["taskkill", "/im", name, "/f"],
                capture_output=True, text=True, timeout=10
            )
            return {"status": "killed" if result.returncode == 0 else "failed",
                   "output": result.stdout or result.stderr}
        else:
            result = subprocess.run(["pkill", name], capture_output=True, text=True, timeout=10)
            return {"status": "killed" if result.returncode == 0 else "failed"}
    except Exception as e:
        return {"error": str(e)}


# Register tools
register_tool(
    name="get_time",
    description="Get current date and time",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_time,
)

register_tool(
    name="system_info",
    description="Get system information (OS, CPU, RAM, GPU, disk)",
    parameters={"type": "object", "properties": {}, "required": []},
    func=system_info,
)

register_tool(
    name="get_clipboard",
    description="Get clipboard contents",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_clipboard,
)

register_tool(
    name="set_clipboard",
    description="Copy text to clipboard",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to copy"}},
        "required": ["text"],
    },
    func=set_clipboard,
)

register_tool(
    name="list_processes",
    description="List running processes",
    parameters={
        "type": "object",
        "properties": {"filter": {"type": "string", "description": "Filter by name"}},
        "required": [],
    },
    func=list_processes,
)
