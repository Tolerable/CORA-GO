#!/usr/bin/env python3
"""
CORA-GO - Mobile AI Assistant
CLI Entry Point

Unity Lab AI + AI-Ministries + TheREV
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    # Files
    read_file, write_file, list_files, search_files,
    # System
    run_shell, system_info, take_screenshot,
    # Web
    web_search, fetch_url, get_weather,
    # Notes
    add_note, get_note, list_notes, search_notes,
    # AI
    query_ollama, query_pollinations, list_ollama_models,
    # Sentinel
    start_sentinel, stop_sentinel, sentinel_status, get_incidents,
    # Bots
    list_bots, launch_bot, stop_bot, running_bots,
    # Voice
    speak_local, get_tts_info
)


# Directories
CORA_GO_DIR = Path.home() / ".cora-go"
CONFIG_FILE = CORA_GO_DIR / "config.json"
PERSONAS_DIR = Path(__file__).parent / "personas"


# Default config
DEFAULT_CONFIG = {
    "persona": "assistant",
    "ai_backend": "ollama",
    "ollama_model": "llama3.2:3b",
    "voice_enabled": False,
    "voice_rate": 150,
    "history_size": 50
}


# Tool registry for natural language dispatching
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "search_files": search_files,
    "run_shell": run_shell,
    "system_info": system_info,
    "screenshot": take_screenshot,
    "web_search": web_search,
    "fetch_url": fetch_url,
    "weather": get_weather,
    "add_note": add_note,
    "get_note": get_note,
    "list_notes": list_notes,
    "search_notes": search_notes,
    "ollama": query_ollama,
    "pollinations": query_pollinations,
    "list_models": list_ollama_models,
    "start_sentinel": start_sentinel,
    "stop_sentinel": stop_sentinel,
    "sentinel_status": sentinel_status,
    "incidents": get_incidents,
    "list_bots": list_bots,
    "launch_bot": launch_bot,
    "stop_bot": stop_bot,
    "running_bots": running_bots,
    "speak": speak_local,
    "tts_info": get_tts_info
}


def ensure_dirs():
    """Create required directories."""
    CORA_GO_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load configuration."""
    ensure_dirs()
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            return {**DEFAULT_CONFIG, **saved}
        except:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """Save configuration."""
    ensure_dirs()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def load_persona(name: str) -> Dict[str, Any]:
    """Load persona configuration."""
    persona_file = PERSONAS_DIR / f"{name}.json"
    if persona_file.exists():
        try:
            return json.loads(persona_file.read_text())
        except:
            pass

    # Default persona
    return {
        "name": name,
        "system_prompt": "You are a helpful AI assistant.",
        "greeting": f"Hello! I'm {name}.",
        "voice": None,
        "temperature": 0.7
    }


def query_ai(prompt: str, config: Dict[str, Any], persona: Dict[str, Any]) -> str:
    """Query AI backend with persona context."""
    system = persona.get("system_prompt", "You are a helpful assistant.")
    temp = persona.get("temperature", 0.7)

    backend = config.get("ai_backend", "ollama")

    if backend == "ollama":
        model = config.get("ollama_model", "llama3.2:3b")
        return query_ollama(prompt, model=model, system=system, temperature=temp)
    else:
        return query_pollinations(prompt, system=system)


def detect_tool_intent(message: str) -> Optional[tuple]:
    """Detect if message wants a tool call."""
    message_lower = message.lower()

    # Direct tool commands
    if message_lower.startswith("/"):
        parts = message[1:].split(maxsplit=1)
        tool_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        if tool_name in TOOLS:
            return (tool_name, args)

    # Natural language detection
    tool_hints = {
        "read_file": ["read file", "show file", "open file", "cat "],
        "write_file": ["write to", "save to", "create file"],
        "list_files": ["list files", "show files", "ls ", "dir "],
        "search_files": ["find files", "search files", "locate"],
        "run_shell": ["run command", "execute", "shell ", "bash "],
        "screenshot": ["screenshot", "capture screen"],
        "web_search": ["search for", "look up", "google", "find online"],
        "fetch_url": ["fetch url", "get page", "download page"],
        "weather": ["weather in", "weather for", "what's the weather"],
        "add_note": ["save note", "remember", "add note"],
        "get_note": ["get note", "recall", "what was"],
        "list_notes": ["list notes", "show notes", "my notes"],
        "search_notes": ["search notes", "find note"],
        "start_sentinel": ["start sentinel", "begin monitoring", "listen"],
        "stop_sentinel": ["stop sentinel", "stop monitoring", "stop listening"],
        "sentinel_status": ["sentinel status", "monitoring status"],
        "incidents": ["show incidents", "what happened", "audio incidents"],
        "list_bots": ["list bots", "available bots", "show bots"],
        "launch_bot": ["launch", "start bot", "run bot"],
        "stop_bot": ["stop bot", "kill bot", "terminate"],
        "running_bots": ["running bots", "active bots"],
        "speak": ["say ", "speak ", "tell me"],
        "list_models": ["list models", "available models", "ollama models"]
    }

    for tool, hints in tool_hints.items():
        for hint in hints:
            if hint in message_lower:
                # Extract the rest as argument
                idx = message_lower.find(hint)
                arg = message[idx + len(hint):].strip()
                return (tool, arg)

    return None


def execute_tool(tool_name: str, arg: str) -> str:
    """Execute a tool with the given argument."""
    if tool_name not in TOOLS:
        return f"Unknown tool: {tool_name}"

    tool = TOOLS[tool_name]

    try:
        # Handle different tool signatures
        if tool_name in ["weather", "system_info", "sentinel_status", "list_bots",
                         "running_bots", "list_notes", "list_models", "tts_info",
                         "screenshot", "incidents"]:
            if arg:
                return tool(arg)
            return tool()

        elif tool_name in ["start_sentinel", "stop_sentinel"]:
            return tool()

        elif tool_name in ["speak", "ollama", "pollinations", "web_search",
                          "fetch_url", "read_file", "get_note", "search_notes",
                          "search_files", "launch_bot", "stop_bot"]:
            if not arg:
                return f"Usage: /{tool_name} <argument>"
            return tool(arg)

        elif tool_name == "run_shell":
            if not arg:
                return "Usage: /run_shell <command>"
            return tool(arg)

        elif tool_name == "write_file":
            # Expect: path content
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return "Usage: /write_file <path> <content>"
            return tool(parts[0], parts[1])

        elif tool_name == "add_note":
            # Expect: key content
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return "Usage: /add_note <key> <content>"
            return tool(parts[0], parts[1])

        else:
            if arg:
                return tool(arg)
            return tool()

    except Exception as e:
        return f"Tool error: {e}"


def interactive_mode(config: Dict[str, Any]):
    """Run interactive chat mode."""
    persona = load_persona(config.get("persona", "assistant"))

    print(f"\n{persona.get('greeting', 'Hello!')}")
    print("Type /help for commands, /quit to exit\n")

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle commands
        if user_input.lower() in ["/quit", "/exit", "/q"]:
            print("Goodbye!")
            break

        if user_input.lower() == "/help":
            print("\nCommands:")
            print("  /quit - Exit")
            print("  /persona <name> - Switch persona")
            print("  /backend <ollama|pollinations> - Switch AI backend")
            print("  /model <name> - Set Ollama model")
            print("  /voice on|off - Toggle voice output")
            print("  /tools - List available tools")
            print("  /<tool> <args> - Run a tool directly")
            print()
            continue

        if user_input.lower().startswith("/persona "):
            name = user_input[9:].strip()
            config["persona"] = name
            save_config(config)
            persona = load_persona(name)
            print(f"Switched to persona: {name}")
            print(persona.get("greeting", f"I'm {name}."))
            continue

        if user_input.lower().startswith("/backend "):
            backend = user_input[9:].strip().lower()
            if backend in ["ollama", "pollinations"]:
                config["ai_backend"] = backend
                save_config(config)
                print(f"Switched to {backend}")
            else:
                print("Valid backends: ollama, pollinations")
            continue

        if user_input.lower().startswith("/model "):
            model = user_input[7:].strip()
            config["ollama_model"] = model
            save_config(config)
            print(f"Model set to: {model}")
            continue

        if user_input.lower().startswith("/voice "):
            state = user_input[7:].strip().lower()
            config["voice_enabled"] = state in ["on", "true", "1", "yes"]
            save_config(config)
            print(f"Voice {'enabled' if config['voice_enabled'] else 'disabled'}")
            continue

        if user_input.lower() == "/tools":
            print("\nAvailable tools:")
            for name in sorted(TOOLS.keys()):
                print(f"  /{name}")
            print()
            continue

        # Check for tool intent
        tool_result = detect_tool_intent(user_input)
        if tool_result:
            tool_name, arg = tool_result
            result = execute_tool(tool_name, arg)
            print(f"\n{result}\n")

            if config.get("voice_enabled"):
                speak_local(result[:200])
            continue

        # Regular AI query
        history.append({"role": "user", "content": user_input})

        # Build context from recent history
        context = "\n".join([
            f"{m['role'].title()}: {m['content']}"
            for m in history[-5:]
        ])

        response = query_ai(user_input, config, persona)
        print(f"\n{persona.get('name', 'Assistant')}: {response}\n")

        history.append({"role": "assistant", "content": response})

        # Trim history
        max_history = config.get("history_size", 50)
        if len(history) > max_history:
            history = history[-max_history:]

        if config.get("voice_enabled"):
            speak_local(response[:500])


def main():
    parser = argparse.ArgumentParser(
        description="CORA-GO - Mobile AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cora_go.py                    # Interactive mode
  cora_go.py -p worker          # Use worker persona
  cora_go.py -q "Hello"         # Single query
  cora_go.py --tool weather     # Run tool directly
  cora_go.py --sentinel         # Start audio sentinel
  cora_go.py --bots             # List available bots
  cora_go.py --launch MYBOT     # Launch a bot
        """
    )

    parser.add_argument("-p", "--persona", help="Persona to use")
    parser.add_argument("-q", "--query", help="Single query (non-interactive)")
    parser.add_argument("-b", "--backend", choices=["ollama", "pollinations"],
                        help="AI backend")
    parser.add_argument("-m", "--model", help="Ollama model")
    parser.add_argument("-v", "--voice", action="store_true", help="Enable voice")

    # Tool shortcuts
    parser.add_argument("--tool", metavar="NAME", help="Run a tool directly")
    parser.add_argument("--args", default="", help="Tool arguments")
    parser.add_argument("--sentinel", action="store_true", help="Start Sentinel")
    parser.add_argument("--bots", action="store_true", help="List bots")
    parser.add_argument("--launch", metavar="BOT", help="Launch a bot")
    parser.add_argument("--status", action="store_true", help="System status")

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Apply command-line overrides
    if args.persona:
        config["persona"] = args.persona
    if args.backend:
        config["ai_backend"] = args.backend
    if args.model:
        config["ollama_model"] = args.model
    if args.voice:
        config["voice_enabled"] = True

    # Handle tool shortcuts
    if args.sentinel:
        print(start_sentinel())
        return

    if args.bots:
        print(list_bots())
        return

    if args.launch:
        print(launch_bot(args.launch))
        return

    if args.status:
        print("CORA-GO Status")
        print("=" * 40)
        print(system_info())
        print()
        print(sentinel_status())
        print()
        print(running_bots())
        return

    if args.tool:
        result = execute_tool(args.tool, args.args)
        print(result)
        return

    if args.query:
        # Single query mode
        persona = load_persona(config.get("persona", "assistant"))
        response = query_ai(args.query, config, persona)
        print(response)
        if config.get("voice_enabled"):
            speak_local(response[:500])
        return

    # Interactive mode
    print("=" * 50)
    print("  CORA-GO - Mobile AI Assistant")
    print("  Unity Lab AI + AI-Ministries + TheREV")
    print("=" * 50)

    interactive_mode(config)


if __name__ == "__main__":
    main()
