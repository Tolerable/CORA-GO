"""
CORA-GO Anchor - Main Entry Point
Windows daemon with smart startup diagnostics.

Usage:
    py anchor/main.py          # Normal startup with GUI
    py anchor/main.py --nogui  # Terminal-only mode
    py anchor/main.py --test   # Run diagnostics only
    py anchor/main.py --quiet  # Skip voice entirely
"""

import sys
import time
import argparse
import threading
from pathlib import Path
from typing import List, Tuple, Callable, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from anchor.config import config
from anchor import tools
from anchor.tools.voice import speak, check_tts
from anchor.tools.system import system_info
from anchor.tools.ai import check_ollama


# ANSI colors for terminal (enable on Windows)
import os
os.system('')  # Enable ANSI on Windows

class C:
    OK = "\033[92m"      # Green
    WARN = "\033[93m"    # Yellow
    FAIL = "\033[91m"    # Red
    INFO = "\033[94m"    # Blue
    END = "\033[0m"

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)


def print_status(name: str, ok: bool, detail: str = ""):
    """Print a status line with color."""
    status = f"{C.OK}OK{C.END}" if ok else f"{C.FAIL}FAIL{C.END}"
    detail_str = f" - {detail}" if detail else ""
    print(f"  [{status}] {name}{detail_str}")


def run_diagnostics(quiet: bool = False, display=None) -> Tuple[List[str], List[str]]:
    """
    Run startup diagnostics.
    Returns: (passed_tests, failed_tests)

    Args:
        quiet: Skip voice output
        display: Optional BootDisplay instance for GUI mode
    """
    passed = []
    failed = []
    problems = []  # For voice announcement

    def log(msg, level='info'):
        """Log to both terminal and display."""
        print(msg)
        if display:
            display.log(strip_ansi(msg), level)

    def update_phase(name, status, msg=""):
        """Update phase in display if available."""
        if display:
            display.update_phase(name, status, msg)

    log(f"\n{C.INFO}CORA-GO Startup Diagnostics{C.END}")
    log("=" * 40)

    # 1. TTS Check
    update_phase("Voice Engine", "running")
    tts = check_tts()
    if tts["available"]:
        passed.append("TTS")
        print_status("Voice (TTS)", True, tts["engine"])
        update_phase("Voice Engine", "ok")
        if display:
            display.log_ok(f"Voice: {tts['engine']}")
    else:
        failed.append("TTS")
        problems.append("voice system")
        print_status("Voice (TTS)", False, "No engine available")
        update_phase("Voice Engine", "fail")
        if display:
            display.log_fail("Voice: No engine available")

    # 2. Ollama Check
    update_phase("AI Backend", "running")
    ollama = check_ollama()
    if ollama.get("available"):
        models = ", ".join(ollama.get("models", [])[:3])
        passed.append("Ollama")
        print_status("Ollama (Local AI)", True, models or "connected")
        update_phase("AI Backend", "ok")
        if display:
            display.log_ok(f"Ollama: {models or 'connected'}")
    else:
        # Not critical - we have Pollinations fallback
        passed.append("Ollama (fallback)")
        print_status("Ollama (Local AI)", False, "Using Pollinations fallback")
        update_phase("AI Backend", "warn")
        if display:
            display.log_warn("Ollama offline, using Pollinations")

    # 3. System Info
    update_phase("Hardware Check", "running")
    try:
        sysinfo = system_info()
        gpu = sysinfo.get("gpu", "none")
        ram = sysinfo.get("ram_available_gb", "?")
        passed.append("System")
        print_status("System", True, f"GPU: {gpu}, RAM: {ram}GB free")
        update_phase("Hardware Check", "ok")
        if display:
            display.log_ok(f"System: GPU={gpu}, RAM={ram}GB")
    except Exception as e:
        failed.append("System")
        problems.append("system monitoring")
        print_status("System", False, str(e))
        update_phase("Hardware Check", "fail")
        if display:
            display.log_fail(f"System: {e}")

    # 4. Tools Registry
    update_phase("Core Tools", "running")
    tool_count = len(tools.list_tools())
    if tool_count > 0:
        passed.append("Tools")
        print_status("Tool Registry", True, f"{tool_count} tools loaded")
        update_phase("Core Tools", "ok")
        if display:
            display.log_ok(f"Tools: {tool_count} loaded")
    else:
        failed.append("Tools")
        problems.append("tool system")
        print_status("Tool Registry", False, "No tools loaded")
        update_phase("Core Tools", "fail")
        if display:
            display.log_fail("Tools: None loaded")

    # 5. Config
    update_phase("Configuration", "running")
    try:
        v = config.get("version")
        passed.append("Config")
        print_status("Configuration", True, f"v{v}")
        update_phase("Configuration", "ok")
        if display:
            display.log_ok(f"Config: v{v}")
    except Exception:
        failed.append("Config")
        print_status("Configuration", False)
        update_phase("Configuration", "fail")
        if display:
            display.log_fail("Config: Load failed")

    # 6. Supabase Relay
    update_phase("Supabase Relay", "running")
    try:
        from anchor.relay import relay
    except ImportError:
        from .relay import relay
    if relay.is_configured():
        passed.append("Relay")
        print_status("Supabase Relay", True, "configured")
        update_phase("Supabase Relay", "ok")
        if display:
            display.log_ok("Relay: Configured")
    else:
        # Not critical for local operation
        print_status("Supabase Relay", False, "Not configured")
        update_phase("Supabase Relay", "warn")
        if display:
            display.log_warn("Relay: Not configured (mobile control disabled)")

    log("=" * 40)

    # Summary
    if not failed:
        log(f"{C.OK}All systems operational.{C.END}\n")
        if display:
            display.set_status("All Systems Operational")
        if not quiet and tts["available"]:
            if display:
                display.start_speaking("CORA-GO online.")
            speak("CORA-GO online.", block=True)
            if display:
                display.stop_speaking()
    else:
        log(f"{C.WARN}{len(failed)} system(s) need attention.{C.END}\n")
        if display:
            display.set_status(f"{len(failed)} System(s) Need Attention")
        if not quiet and tts["available"] and problems:
            problem_text = ", ".join(problems)
            msg = f"CORA-GO online with issues. {problem_text} unavailable."
            if display:
                display.start_speaking(msg)
            speak(msg, block=True)
            if display:
                display.stop_speaking()

    return passed, failed


def main_loop():
    """Main daemon loop - process commands, check relay."""
    try:
        from anchor.relay import relay
    except ImportError:
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


def run_with_gui(args):
    """Run CORA-GO with the visual boot display."""
    from anchor.ui import BootDisplay

    display = BootDisplay()
    display.create_window()

    # Set up boot phases
    phases = [
        "Voice Engine",
        "AI Backend",
        "Hardware Check",
        "Core Tools",
        "Configuration",
        "Supabase Relay",
    ]
    display.set_phases(phases)

    def boot_sequence():
        """Run boot sequence in background thread."""
        time.sleep(0.5)  # Let GUI render

        # Run diagnostics with display integration
        passed, failed = run_diagnostics(quiet=args.quiet, display=display)

        if args.test:
            time.sleep(2)
            display.close()
            return

        # Check for critical failures
        critical = ["Tools", "Config"]
        critical_failed = [f for f in failed if f in critical]

        if critical_failed:
            display.log_fail("Critical systems failed. Cannot start.")
            display.set_status("CRITICAL FAILURE - Cannot Start")
            if not args.quiet:
                speak("CORA-GO cannot start. Critical system failure.", block=True)
            time.sleep(3)
            display.close()
            return

        # Enable chat mode
        display.enable_chat_mode()

        # Start relay if configured
        try:
            from anchor.relay import relay
        except ImportError:
            from .relay import relay
        if relay.is_configured():
            relay.start()
            display.log_ok("Relay connected - mobile control enabled")
        else:
            display.log_warn("Relay not configured - run with --setup-relay")

    # Run boot in background thread
    boot_thread = threading.Thread(target=boot_sequence, daemon=True)
    boot_thread.start()

    # Run GUI mainloop (blocks)
    display.run()


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="CORA-GO Anchor Daemon")
    parser.add_argument("--test", action="store_true", help="Run diagnostics only")
    parser.add_argument("--quiet", action="store_true", help="No voice output")
    parser.add_argument("--nogui", action="store_true", help="Terminal-only mode (no GUI)")
    args = parser.parse_args()

    # GUI mode is default
    if not args.nogui:
        try:
            run_with_gui(args)
            return
        except ImportError as e:
            print(f"{C.WARN}GUI not available ({e}), falling back to terminal{C.END}")
        except Exception as e:
            print(f"{C.WARN}GUI error ({e}), falling back to terminal{C.END}")

    # Terminal mode
    passed, failed = run_diagnostics(quiet=args.quiet)

    if args.test:
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
