# CORA-GO Vision & Architecture

**Cognitive Operations & Reasoning Assistant - Global Outreach**

**Version:** 2.0.0-alpha
**Date:** 2025-12-25
**Status:** Active Development
**Origin:** Merged from Unity Lab AI (CORA) + AI-Ministries (MINIBOT)

## Overview

CORA-GO is a **two-part system**:
1. **PC Anchor** - Windows daemon with full hardware access, voice, tools
2. **Mobile Remote** - Handheld control panel that talks to PC via Supabase

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SUPABASE                                │
│  (relay: commands, responses, status, notifications)           │
└─────────────────────────────────────────────────────────────────┘
        ▲                                         ▲
        │ HTTP/REST                               │ HTTP/REST
        ▼                                         ▼
┌─────────────────────┐                 ┌─────────────────────┐
│    PC ANCHOR        │                 │   MOBILE REMOTE     │
│    (Windows)        │                 │   (PWA)             │
├─────────────────────┤                 ├─────────────────────┤
│ • Full Python tools │                 │ • Control panel UI  │
│ • Voice I/O (Kokoro)│                 │ • Send commands     │
│ • Screenshots       │                 │ • View responses    │
│ • System control    │                 │ • Standalone chat   │
│ • File access       │                 │ • Camera/GPS tools  │
│ • Ollama local      │                 │ • Pollinations AI   │
│ • KITT-style UI     │                 │                     │
│ • Exposes API       │                 │                     │
└─────────────────────┘                 └─────────────────────┘
```

## Directory Structure

```
CORA-GO/
├── README.md
├── VISION.md              # This file
├── requirements.txt       # Python deps for PC
│
├── anchor/                # PC DAEMON
│   ├── __init__.py
│   ├── main.py           # Entry point, startup sequence
│   ├── config.py         # Configuration management
│   ├── api.py            # HTTP API for mobile/external
│   ├── relay.py          # Supabase relay handler
│   ├── ui.py             # KITT-style minimal GUI
│   │
│   └── tools/            # Modular tool system
│       ├── __init__.py   # Tool registry
│       ├── voice.py      # TTS (Kokoro) + STT
│       ├── system.py     # System info, processes, clipboard
│       ├── files.py      # File operations
│       ├── screenshots.py # Screen/window capture
│       ├── windows.py    # Window management
│       ├── media.py      # Media playback control
│       ├── web.py        # Web search, fetch
│       ├── ai.py         # Ollama/Pollinations routing
│       ├── notes.py      # Persistent notes
│       └── shell.py      # Safe shell execution
│
├── web/                   # MOBILE REMOTE (PWA)
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js
│   ├── css/
│   │   └── cora-go.css
│   ├── js/
│   │   ├── app.js        # Main app
│   │   ├── relay.js      # PC communication via Supabase
│   │   ├── tools.js      # Browser-based tools
│   │   └── ui.js         # Control panel UI
│   └── assets/
│
└── shared/                # Shared constants/types
    ├── commands.py       # Command definitions
    └── commands.js       # Same for JS
```

## Voice Startup Sequence

```python
# On boot, anchor runs diagnostics:
startup_checks = [
    ("ollama", check_ollama),      # Is Ollama running?
    ("voice", check_tts),          # Can we speak?
    ("supabase", check_relay),     # Can we reach relay?
    ("screenshot", check_screen),  # Can we capture?
]

# Smart startup voice:
# - If ALL pass: "CORA-GO online." (short)
# - If SOME fail: "CORA-GO online. [problem] disabled, attempting repair."
# - If repair works: Continue silently
# - If repair fails: "Unable to repair [system]. Notifying user."
# - If CRITICAL fail: "CORA-GO cannot start. [reason]. Check logs."
```

## Tool Inheritance

Best of both projects:

| Feature | Source | Notes |
|---------|--------|-------|
| Modular tools structure | CORA | 20 separate files |
| Kokoro TTS | CORA | Neural voice with emotion |
| Function calling | MINIBOT | OpenAI-compatible |
| Task routing | MINIBOT | Simple→Ollama, Complex→Cloud |
| Safety system | MINIBOT | Blocked/confirm/warn commands |
| Colab integration | MINIBOT | Bot messaging pattern |
| Window layouts | CORA | Cascade/tile/grid |
| Self-modification | CORA | Runtime script creation |
| Persona system | MINIBOT | 9 built-in personas |

## Supabase Relay Schema

```sql
-- Commands from mobile to PC
CREATE TABLE cora_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL,           -- Which mobile sent it
    command TEXT NOT NULL,             -- Tool name
    params JSONB DEFAULT '{}',         -- Tool parameters
    status TEXT DEFAULT 'pending',     -- pending/running/done/error
    result JSONB,                      -- Response from PC
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- PC status (heartbeat)
CREATE TABLE cora_status (
    id TEXT PRIMARY KEY DEFAULT 'anchor',
    online BOOLEAN DEFAULT false,
    last_seen TIMESTAMPTZ,
    system_info JSONB,                 -- CPU, RAM, GPU, etc.
    active_tools JSONB                 -- What's currently running
);
```

## Build Order

1. **anchor/tools/** - Port tools from CORA, modular
2. **anchor/main.py** - Startup with smart diagnostics
3. **anchor/api.py** - HTTP API for control
4. **anchor/relay.py** - Supabase polling
5. **web/js/relay.js** - Mobile→Supabase→PC
6. **web/js/app.js** - Control panel UI

## Credits

- **Unity Lab AI** (Hackall360, Sponge, GFourteen) - CORA core
- **AI-Ministries** (TheREV) - MINIBOT, Colab patterns, tool calling
