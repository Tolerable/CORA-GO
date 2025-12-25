# CORA-GO WORK LOG

**Last Updated:** 2025-12-25 17:45
**Status:** Active Development
**For:** GEE's Christmas Gift

---

## WHAT CORA-GO IS

CORA-GO = **Colab Lite + Remote PC Control + AI Assistant**

Two connected systems:
1. **PC Anchor** - Windows daemon with tools, bots, screen sharing
2. **Web Control Panel** - Mobile PWA with TWO views:
   - **TeamViewer Mode** - Live screen view of PC, remote control
   - **Colab Mode** - Team chat, projects, brain, bot management

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPABASE (EZTUNES-LIVE)                  │
│  Tables: cora_status, cora_commands, cora_chat, cora_team   │
│          cora_projects, cora_brain, cora_screens            │
└─────────────────────────────────────────────────────────────┘
        ▲                                         ▲
        │                                         │
┌───────┴───────┐                       ┌─────────┴─────────┐
│  PC ANCHOR    │                       │  WEB PANEL        │
│  (Windows)    │                       │  (PWA)            │
├───────────────┤                       ├───────────────────┤
│ • 64 tools    │                       │ VIEW 1: TeamViewer│
│ • Bot runner  │                       │ • Live screen     │
│ • Screen cap  │                       │ • Mouse/keyboard  │
│ • Minibot CLI │                       │ • File transfer   │
│ • C.O.R.A     │                       ├───────────────────┤
│               │                       │ VIEW 2: Colab     │
│               │                       │ • Team chat       │
│               │                       │ • Projects        │
│               │                       │ • Brain/memory    │
│               │                       │ • Bot control     │
│               │                       │ • AI chat         │
└───────────────┘                       └───────────────────┘
```

---

## CURRENT STATE (What's Built)

### PC Anchor ✓
- [x] 64 tools registered (voice, system, files, ai, media, nas, vision, etc.)
- [x] Relay to Supabase (heartbeat, commands)
- [x] Bot management (list, launch, stop)
- [x] Config system
- [x] Pairing system

### Web Panel - Partial
- [x] Pairing flow (QR scan)
- [x] PC status display
- [x] Basic chat (Pollinations)
- [x] Quick actions (6 tools)
- [x] Bot tab (list, launch, stop)
- [x] Setup page (services config)
- [ ] TeamViewer mode
- [ ] Team chat
- [ ] Projects
- [ ] Brain

---

## BUILD PLAN

### Phase 1: TeamViewer Mode (screen.html)
Live view of PC desktop with interaction.

**New table:** `cora_screens`
```sql
CREATE TABLE cora_screens (
    id TEXT PRIMARY KEY,  -- anchor_id
    image_data TEXT,      -- base64 screenshot
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    width INT,
    height INT
);
```

**PC Anchor changes:**
- Continuous screenshot capture (every 1-2 seconds)
- Upload to cora_screens table
- Handle mouse/keyboard commands from mobile

**Web panel (screen.html):**
- Full-screen view of PC desktop
- Touch/click sends mouse events
- Keyboard input sends key events
- Pinch to zoom
- Connection status indicator

### Phase 2: Team Chat (chat system)
Like Colab's chat but simpler.

**New table:** `cora_chat`
```sql
CREATE TABLE cora_chat (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT NOT NULL,
    sender TEXT NOT NULL,      -- 'user', 'minibot', bot name
    message TEXT NOT NULL,
    msg_type TEXT DEFAULT 'text',  -- text, command, response, error
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Features:**
- Messages from user
- Messages from Minibot (AI responses)
- Messages from other bots
- Command execution results
- Real-time updates via polling

### Phase 3: Minibot CLI
The AI that runs on PC and takes commands.

**Minibot capabilities:**
- Receives messages from cora_chat
- Parses natural language → tool calls
- Executes tools
- Posts results back to chat
- Can use Ollama or Pollinations

**Integration:**
- Part of PC Anchor
- Always listening for commands
- Can be addressed directly: "@minibot do X"
- Or responds to general questions

### Phase 4: Projects
Simple project tracking.

**New table:** `cora_projects`
```sql
CREATE TABLE cora_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    tasks JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Features:**
- Create/edit projects
- Add tasks with status
- View project list
- Filter by status

### Phase 5: Brain (Shared Memory)
Knowledge base for the team.

**New table:** `cora_brain`
```sql
CREATE TABLE cora_brain (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);
```

**Features:**
- Store facts/knowledge
- Query by key or category
- Minibot can read/write
- Persists across sessions

---

## FILE STRUCTURE (To Build)

```
web/
├── index.html      ✓ Main app (Colab view)
├── pair.html       ✓ Pairing
├── setup.html      ✓ Service config
├── screen.html     ✓ TeamViewer mode
├── js/
│   ├── app.js      ✓ Main app logic
│   ├── relay.js    ✓ Supabase communication
│   ├── chat.js     ✓ Team chat
│   └── brain.js    ← TODO: Brain interface
└── css/
    └── cora-go.css ✓ Styles

anchor/
├── main.py         ✓ Entry point
├── relay.py        ✓ Supabase relay
├── pairing.py      ✓ QR pairing
├── config.py       ✓ Config management
├── coramini.py     ✓ AI assistant (CORAMINI)
├── screen_share.py ✓ Screen capture for TeamViewer
└── tools/          ✓ 64 tools
```

---

## PROGRESS (2025-12-25)

DONE:
- [x] Migration 006_full_features.sql - RAN IN SUPABASE ✓
- [x] screen.html - TeamViewer view created
- [x] screen_share.py - PC screen capture module
- [x] Screen tab added to index.html navigation
- [x] screen_share started in main.py (GUI + terminal modes)
- [x] Team chat tab added to index.html
- [x] chat.js - Team chat module with polling
- [x] CORAMINI (coramini.py) - AI assistant that monitors team chat
- [x] CORAMINI started in main.py

NEXT:
- [ ] Test end-to-end on GEE's PC
- [ ] Add Projects tab
- [ ] Add Brain tab

---

## NOTES FOR AFTER COMPACT

- Supabase: EZTUNES-LIVE (bugpycickribmdfprryq)
- Key: sb_publishable_c9Q2joJ8g7g7ntdrzbnzbA_RJfa_5jt
- Backup at: C:/claude/CORA-GO-BACKUP-2025-12-25.zip
- 64 tools already working
- Pairing flow working
- This is for GEE's Christmas gift
