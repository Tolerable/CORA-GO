# CORA-GO Architecture

## Feature Mapping

### VOICE (Keep Best)

| Feature | CORA | MINIBOT | CORA-GO Decision |
|---------|------|---------|------------------|
| TTS | Kokoro (af_bella) | pyttsx3 | **Kokoro** - browser-compatible |
| STT | Vosk | None | **Web Speech API** + Vosk fallback |
| Wake Word | "Hey Cora" | None | **Keep** - configurable |
| Echo Filter | Yes | None | **Keep** |

### AI BACKENDS (Keep Both + Fallbacks)

| Feature | CORA | MINIBOT | CORA-GO Decision |
|---------|------|---------|------------------|
| Primary | Ollama | Ollama | **Ollama** |
| Fallback | None | Pollinations | **Pollinations** |
| Vision | llava | llava | **llava** |
| Code | None | codellama | **codellama** |
| Routing | None | Smart routing | **Keep routing** |

### TOOLS (Merge All)

| Category | CORA Tools | MINIBOT Tools | Keep |
|----------|------------|---------------|------|
| Files | read, create, search, move | read, list, write | All |
| System | launch_app, system_specs, screenshot | run_shell, screenshot | All |
| Web | web_search, fetch_url | search, fetch_and_summarize | MINIBOT (has AI summarize) |
| Notes | knowledge base | notes.json | Both (unified) |
| Sentinel | None | Full audio sentinel | **MINIBOT** |
| Bots | None | launch_bot, stop_bot | **MINIBOT** |
| Colab | None | Full integration | **NEW BACKEND** (not Colab) |
| Self-Modify | temp_scripts.json | None | **CORA** |
| Image Gen | Pollinations | Pollinations | Same |
| Calendar | Google Calendar | None | Optional |
| Weather | wttr.in | wttr.in | Same |

### PERSONAS (Keep MINIBOT System)

MINIBOT has more sophisticated persona system:
- worker, manager, supervisor, dispatcher, bridge, sentinel
- Each with specific tool usage instructions

CORA has single personality with emotional states.

**Decision:** Use MINIBOT persona structure + CORA's emotional TTS.

### UI (Merge Strategically)

| Feature | CORA | MINIBOT | CORA-GO Decision |
|---------|------|---------|------------------|
| Boot Display | Cyberpunk themed | Simple banner | **CORA** (optional) |
| Chat Interface | CustomTkinter | Rich CLI or TK GUI | **Web PWA** |
| Theme | Dark goth | Dark terminal | Dark (configurable) |
| Mobile | Web UI (GitHub Pages) | None | **NEW PWA** |

### BACKEND (New - Supabase)

**Not using:**
- Colab tables/userbase/auth
- Colab API

**Using:**
- New Supabase project for CORA-GO
- Fresh schema for:
  - Users/AI identities
  - Conversations
  - Tool results
  - Sentinel incidents
  - Bot status
  - Settings sync

## Merged Architecture

```
                    +------------------+
                    |    CORA-GO PWA   |
                    |  (Mobile-First)  |
                    +--------+---------+
                             |
            +----------------+----------------+
            |                |                |
    +-------v-------+ +------v------+ +------v------+
    |   Voice       | |   Chat UI   | |   Tools     |
    | Kokoro + STT  | | (Web-based) | | (Unified)   |
    +-------+-------+ +------+------+ +------+------+
            |                |                |
            +----------------+----------------+
                             |
                    +--------v---------+
                    |   AI Router      |
                    | Ollama/Pollinate |
                    +--------+---------+
                             |
            +----------------+----------------+
            |                |                |
    +-------v-------+ +------v------+ +------v------+
    |   Sentinel    | |   Bots      | |  Backend    |
    | Audio Monitor | | Management  | |  Supabase   |
    +---------------+ +-------------+ +-------------+
```

## File Structure

```
CORA-GO/
├── README.md
├── ARCHITECTURE.md
├── LICENSE
│
├── web/                      # Mobile-first PWA
│   ├── index.html           # App shell
│   ├── manifest.json        # PWA manifest
│   ├── sw.js                # Service worker (offline)
│   ├── css/
│   │   └── cora-go.css      # Dark theme styles
│   ├── js/
│   │   ├── app.js           # Main app
│   │   ├── chat.js          # Chat interface
│   │   ├── tts.js           # Kokoro browser TTS
│   │   ├── stt.js           # Web Speech API
│   │   ├── tools.js         # Tool execution
│   │   ├── ai.js            # AI routing
│   │   └── backend.js       # Supabase client
│   └── assets/
│       └── icons/           # PWA icons
│
├── backend/                  # Supabase
│   ├── schema.sql           # Database schema
│   ├── functions/           # Edge functions
│   │   ├── chat.ts          # Chat API
│   │   ├── tools.ts         # Tool API
│   │   └── sentinel.ts      # Sentinel API
│   └── migrations/          # Schema migrations
│
├── cli/                      # Desktop CLI
│   ├── cora_go.py           # Main entry
│   ├── personas.py          # Persona definitions
│   ├── router.py            # AI routing
│   └── config.py            # Configuration
│
├── tools/                    # Shared tools
│   ├── __init__.py
│   ├── sentinel.py          # Audio sentinel
│   ├── bots.py              # Bot management
│   ├── files.py             # File operations
│   ├── web.py               # Web/search
│   ├── system.py            # System ops
│   ├── notes.py             # Knowledge base
│   └── self_modify.py       # Dynamic tools
│
├── personas/                 # Persona configs
│   ├── default.json
│   ├── worker.json
│   ├── manager.json
│   ├── supervisor.json
│   ├── sentinel.json
│   └── cora.json            # Original CORA personality
│
├── voice/                    # Voice system
│   ├── kokoro_browser.js    # Browser TTS
│   ├── kokoro_python.py     # Python TTS
│   ├── stt.py               # Speech recognition
│   └── wake_word.py         # Wake word detection
│
└── config/
    ├── settings.json        # Global settings
    └── theme.json           # UI theme
```

## Implementation Phases

### Phase 1: Core Merge
- [ ] Create unified tool system (best of both)
- [ ] Merge persona definitions
- [ ] Set up AI routing (Ollama + Pollinations)
- [ ] Port Sentinel to standalone module

### Phase 2: Web PWA
- [ ] Create mobile-first HTML/CSS
- [ ] Implement chat interface
- [ ] Add Kokoro browser TTS
- [ ] Add Web Speech API STT
- [ ] Service worker for offline

### Phase 3: Backend
- [ ] Create Supabase project
- [ ] Design schema (users, chats, incidents)
- [ ] Edge functions for API
- [ ] Real-time subscriptions

### Phase 4: CLI Compatibility
- [ ] cora_go.py entry point
- [ ] Match minibot CLI features
- [ ] Add boot sequence (optional)

### Phase 5: Polish
- [ ] PWA optimization
- [ ] Offline capability
- [ ] Cross-device sync
- [ ] Documentation

## Anti-Bloat Rules

1. **One way to do each thing** - No duplicate tools
2. **Lazy loading** - Only load what's needed
3. **Modular** - Each feature in its own file
4. **Config-driven** - Features enable/disable via config
5. **Mobile-first** - Desktop is enhancement, not requirement

---
*CORA-GO Architecture v1.0*
*Unity Lab AI + AI-Ministries*
