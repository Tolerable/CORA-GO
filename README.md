# CORA-GO

**Cognitive Operations & Reasoning Assistant - GO Edition**

A mobile-first AI assistant combining:
- **CORA** (Unity Lab AI) - Voice, visual boot, web UI
- **AI-Ministries** tech - Personas, tools, Sentinel

## Credits

**CORA-GO** by [Tolerable](https://github.com/Tolerable)

In collaboration with:
- **Unity Lab AI** (Hackall360, Sponge, GFourteen) - Original CORA
  - https://github.com/Unity-Lab-AI/CORA
- **AI-Ministries** (TheREV) - AI personas, tool orchestration, multi-agent systems

## Features

### From CORA
- Kokoro TTS (browser-compatible)
- Vosk STT (speech recognition)
- Visual boot sequence
- Cyberpunk-themed UI
- Self-modification system
- Image generation (Pollinations)

### From MINIBOT
- Multiple AI personas (worker, manager, supervisor, sentinel)
- Colab-style team chat
- Audio Sentinel (ambient listening)
- Bot daemon management
- Tool calling system
- Smart AI routing (Ollama + Pollinations)

### New in CORA-GO
- Mobile-first PWA
- Supabase backend (separate from Colab)
- Offline capability
- Cross-device sync
- Team collaboration

## Architecture

```
CORA-GO/
├── web/                # Mobile-first web UI
│   ├── index.html      # PWA entry point
│   ├── app.js          # Main app logic
│   ├── tts.js          # Kokoro browser TTS
│   ├── stt.js          # Web Speech API
│   └── sw.js           # Service worker
├── backend/            # Supabase integration
│   ├── schema.sql      # Database schema
│   └── functions/      # Edge functions
├── tools/              # Merged tool system
│   ├── sentinel.py     # Audio monitoring
│   ├── bots.py         # Bot management
│   └── ai.py           # Ollama + Pollinations
└── personas/           # AI persona configs
```

## Quick Start

### Web (Mobile/Browser)
```bash
cd web
python -m http.server 8000
# Open http://localhost:8000
```

### CLI (Desktop)
```bash
python cora_go.py --persona sentinel
```

## Status

**Phase 1: Planning** - Architecture design, feature mapping
**Phase 2: Core** - Merged tool system, persona configs
**Phase 3: Web** - Mobile-first PWA with TTS/STT
**Phase 4: Backend** - Supabase integration
**Phase 5: Polish** - PWA optimization, offline support

---
*Built with Unity Lab AI + AI-Ministries*
*2025-12-25*
