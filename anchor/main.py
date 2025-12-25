"""
CORA-GO Anchor - Main Entry Point
Windows daemon with smart startup diagnostics.

Usage:
    py anchor/main.py          # Normal startup
    py anchor/main.py --test   # Run diagnostics only
    py anchor/main.py --quiet  # Skip voice entirely
"""

import sys
import time
import argparse
from pathlib import Path
from typing import List, Tuple, Callable

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from anchor.config import config
from anchor import tools
from anchor.tools.voice import speak, check_tts
from anchor.tools.system import system_info
from anchor.tools.ai import check_ollama


# ANSI colors for terminal
class C:
    OK = "\033[92m"      # Green
    WARN = "\033[93m"    # Yellow
    FAIL = "\033[91m"    # Red
    INFO = "\033[94m"    # Blue
    END = "\033[0m"


def print_status(name: str, ok: bool, detail: str = ""):
    """Print a status line with color."""
    status = f"{C.OK}OK{C.END}" if ok else f"{C.FAIL}FAIL{C.END}"
    detail_str = f" - {detail}" if detail else ""
    print(f"  [{status}] {name}{detail_str}")


def run_diagnostics(quiet: bool = False) -> Tuple[List[str], List[str]]:
    """
    Run startup diagnostics.
    Returns: (passed_tests, failed_tests)
    """
    passed = []
    failed = []
    problems = []  # For voice announcement
    
    print(f"\n{C.INFO}CORA-GO Startup Diagnostics{C.END}")
    print("=" * 40)
    
    # 1. TTS Check
    tts = check_tts()
    if tts["available"]:
        passed.append("TTS")
        print_status("Voice (TTS)", True, tts["engine"])
    else:
        failed.append("TTS")
        problems.append("voice system")
        print_status("Voice (TTS)", False, "No engine available")
    
    # 2. Ollama Check
    ollama = check_ollama()
    if ollama.get("available"):
        models = ", ".join(ollama.get("models", [])[:3])
        passed.append("Ollama")
        print_status("Ollama (Local AI)", True, models or "connected")
    else:
        # Not critical - we have Pollinations fallback
        passed.append("Ollama (fallback)")
        print_status("Ollama (Local AI)", False, "Using Pollinations fallback")
    
    # 3. System Info
    try:
        sysinfo = system_info()
        gpu = sysinfo.get("gpu", "none")
        ram = sysinfo.get("ram_available_gb", "?")
        passed.append("System")
        print_status("System", True, f"GPU: {gpu}, RAM: {ram}GB free")
    except Exception as e:
        failed.append("System")
        problems.append("system monitoring")
        print_status("System", False, str(e))
    
    # 4. Tools Registry
    tool_count = len(tools.list_tools())
    if tool_count > 0:
        passed.append("Tools")
        print_status("Tool Registry", True, f"{tool_count} tools loaded")
    else:
        failed.append("Tools")
        problems.append("tool system")
        print_status("Tool Registry", False, "No tools loaded")
    
    # 5. Config
    try:
        v = config.get("version")
        passed.append("Config")
        print_status("Configuration", True, f"v{v}")
    except Exception:
        failed.append("Config")
        print_status("Configuration", False)
    
    print("=" * 40)
    
    # Summary
    if not failed:
        print(f"{C.OK}All systems operational.{C.END}\n")
        if not quiet and tts["available"]:
            speak("CORA-GO online.", block=True)
    else:
        print(f"{C.WARN}{len(failed)} system(s) need attention.{C.END}\n")
        if not quiet and tts["available"] and problems:
            problem_text = ", ".join(problems)
            speak(f"CORA-GO online with issues. {problem_text} unavailable.", block=True)
    
    return passed, failed


def main_loop():
    """Main daemon loop - process commands, check relay."""
    from .relay import relay

    print(f"{C.INFO}Entering main loop (Ctrl+C to exit){C.END}")

    # Start relay if configured
    if relay.is_configured():
        relay.start()
        print(f"{C.OK}Relay connected to Supabase{C.END}")
    else:
        print(f"{C.WARN}Relay not configured - mobile control disabled{C.END}")
        print(f"  Run: py anchor/main.py --setup-relay")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{C.WARN}Shutting down...{C.END}")
        relay.stop()
        speak("CORA-GO shutting down.", block=True)


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="CORA-GO Anchor Daemon")
    parser.add_argument("--test", action="store_true", help="Run diagnostics only")
    parser.add_argument("--quiet", action="store_true", help="No voice output")
    args = parser.parse_args()
    
    # Run diagnostics
    passed, failed = run_diagnostics(quiet=args.quiet)
    
    if args.test:
        # Just diagnostics, exit
        sys.exit(0 if not failed else 1)
    
    # Check for critical failures
    critical = ["Tools", "Config"]
    critical_failed = [f for f in failed if f in critical]
    
    if critical_failed:
        print(f"{C.FAIL}Critical systems failed. Cannot start.{C.END}")
        if not args.quiet:
            speak("CORA-GO cannot start. Critical system failure.", block=True)
        sys.exit(1)
    
    # Enter main loop
    main_loop()


if __name__ == "__main__":
    main()
