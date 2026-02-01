# Fractured Survival - NPC Management System

## Project Overview
A standalone, high-intelligence NPC service for the game "Fractured Survival". The core architecture decouples the NPC's "Thinking" (AI Brain) from its "Acting" (Game Engine).

## User Personas
- **Game Developers**: Need API integration for NPCs in Unreal Engine
- **Content Creators**: Use web dashboard to create and manage NPCs
- **Players**: Interact with NPCs that remember them and evolve

## Core Requirements
1. **Cognitive Architecture**: Double-Pass logic (internal monologue + public response)
2. **Persistent Memory**: NPCs remember interactions, personalities evolve over time
3. **Cognitive Frame**: JSON schema for all NPC communication
4. **Multi-Player Support**: NPCs track individual players with separate reputations
5. **Social Dynamics**: NPC-to-NPC relationships and gossip system

---

## Architecture

### Service Architecture
```
Frontend (React) --> Backend (FastAPI Proxy) --> NPC Service (Port 9000)
                           |
                           v
                       MongoDB (Web data)
                           |
                       SQLite (NPC memory)
```

### Key Components
- **NPC Service** (`/app/npc_system/npc_service.py`): Core brain service on port 9000
- **Advanced Intelligence** (`/app/npc_system/core/advanced_intelligence.py`): Player tracking, relationships, gossip
- **Web Backend** (`/app/backend/server.py`): Proxy to NPC service
- **Frontend** (`/app/frontend/src/App.js`): NPC Management Dashboard

---

## Implementation Phases

### Phase 1: Standalone Simulation - COMPLETE
- [x] NPC cognitive system with double-pass logic
- [x] Limbic system (emotions, vitals)
- [x] Personality evolution
- [x] Memory persistence (SQLite)

### Phase 2: Engine Integration - COMPLETE
- [x] FastAPI service on port 9000
- [x] Supervisor process management
- [x] API proxy through web backend
- [x] CORS handling

### Phase 3: Advanced Intelligence - COMPLETE (Jan 29-30, 2025)
- [x] Player session management (PlayerManager)
- [x] Individual reputation per player per NPC
- [x] NPC-to-NPC relationships (NPCRelationshipGraph)
- [x] Gossip & rumor system (GossipSystem)
- [x] Frontend Players tab
- [x] Reputation display in chat
- [x] **Topic Memory System** - NPCs remember conversation topics (family, goals, fears, secrets, crimes)
- [x] **Memory Log UI** - Shows what NPCs remember about players
- [x] **Memory Sharing Between NPCs** - NPCs gossip and share what they learned about players
- [x] **Secondhand Knowledge** - NPCs can act on information they heard from other NPCs
- [x] **Memory Decay System** - Memories fade over time; important memories decay slower
- [x] **Memory Reinforcement** - Mentioning topics refreshes memory strength
- [x] **Dynamic Quest Generation** - NPCs generate quests based on memories about players
- [x] **World Simulation Mode** - Background system that automatically advances time, decays memories, triggers gossip, and generates events
- [x] **World Controls UI** - Frontend tab with start/stop, time scale, stats, event feed
- [x] **Faction System** - 4 factions (Guards, Traders, Citizens, Outcasts) with dynamic relations
- [x] **Faction Events** - Skirmishes, betrayals, alliances that affect faction relations
- [x] **Player Faction Reputation** - Track player standing with each faction with ripple effects

### Phase 5: Global Scaling - COMPLETE (Jan 30, 2026)
- [x] **Connection Pooling** - SQLite connection pool with 10 connections, WAL mode
- [x] **TTL Cache** - LRU cache with 5000 items, 300s TTL, 0.1ms access time
- [x] **Tiered Update System** - Active/Nearby/Idle/Dormant tiers for efficient processing
- [x] **Batch Operations** - Batch memory decay, cleanup, and NPC data retrieval
- [x] **Database Indexes** - 24+ performance indexes on frequently queried columns
- [x] **Paginated APIs** - `/npc/list/paginated`, `/players/paginated`, `/quests/paginated`
- [x] **Batch Endpoints** - `/batch/init`, `/batch/interact` for multi-NPC operations
- [x] **Zone-based Processing** - `/zone/{id}/tick`, `/zone/{id}/register`
- [x] **Performance Monitoring** - Request latency tracking, cache hit rates

### Voice System - ENHANCED (Jan 30, 2026)
- [x] **ElevenLabs Integration** - 21 pre-made voices for NPCs
- [x] **Gender-Specific Voice Maps** - Separate male/female voice pools
- [x] **Unique Voice Assignment** - Each NPC guaranteed unique voice from their gender's pool
- [x] **Personality-Based Fingerprints** - Each NPC gets unique voice characteristics:
  - Stability modifier based on discipline/aggression/paranoia
  - Similarity modifier based on empathy/discipline
  - Style modifier based on romanticism/curiosity
  - Speed modifier based on risk_tolerance/aggression
- [x] **Voice Assignment** - Auto-assigns voices based on NPC role, gender, faction, AND personality
- [x] **Pitch Descriptions** - Each NPC tagged: harsh/warm/nervous/controlled/expressive/normal
- [x] **Voice Cloning** - Upload audio samples to create custom NPC voices (IVC)
- [x] **Mood Adjustments** - 10 moods affect voice in real-time (angry, sad, happy, fearful, etc.)
- [x] **Auto-Play** - NPC responses automatically play with voice (toggle ON/OFF)
- [x] **Stop Button** - Interrupt voice playback at any time
- [x] **Voice Reset APIs** - Reset individual or all voice assignments to fix conflicts
- [x] **Voice Profiles:**
  - Male: Adam, Arnold, Clyde, Antoni, Josh, Ethan, Sam, Daniel, Charlie, Harry, James
  - Female: Rachel, Domi, Bella, Elli, Emily, Grace, Charlotte, Serena, Glinda, Mimi

### Speech-to-Text System - NEW (Jan 30, 2026)
- [x] **OpenAI Whisper Integration** - Transcribe player speech via Emergent LLM key
- [x] **Microphone UI** - Push-to-talk style recording in chat panel
- [x] **Recording Indicator** - Visual feedback showing recording time
- [x] **Auto-Transcription** - Audio automatically sent to backend after recording stops
- [x] **Text Population** - Transcribed text fills chat input for review before sending

### Voice Visualizer - NEW (Jan 30, 2026)
- [x] **SiriWave Integration** - Animated wave visualization when NPC speaks
- [x] **Dynamic Animation** - Waves speed up and amplify when audio plays
- [x] **Theme Matching** - Rust orange color matching game aesthetic
- [x] **Status Indicator** - "Voice Ready" / "NPC is speaking..." states
- [x] **Scanline Effect** - Retro CRT-style overlay for immersive feel

### Security Lockdown - NEW (Jan 30, 2026)
- [x] **Login Required** - No features accessible without authentication
- [x] **Dedicated Login Page** - Full-screen with game logo and branding
- [x] **Session Management** - JWT tokens with localStorage persistence
- [x] **Logout Functionality** - Clear session and return to login page

### UI/UX Polish - NEW (Jan 30, 2026)
- [x] **Game Theme Matching** - Colors match Fractured Survival logo (rust orange, military green, dark grays)
- [x] **Professional Header** - Logo, title, user greeting, logout button
- [x] **Styled Tabs** - Rust orange accent on active tab
- [x] **Improved Chat Bubbles** - Player (green) vs NPC (dark) styling
- [x] **Polished Input Area** - Better send button, mic button, textarea styling
- [x] **Quick Select Bar** - Easy NPC switching at bottom of screen

### Authentication System - NEW (Jan 30, 2026)
- [x] **User Registration** - Web users can create accounts with username, password, email
- [x] **User Login** - Authenticate with username/email and password
- [x] **JWT Tokens** - Secure token-based authentication with 1-week expiration
- [x] **Password Hashing** - SHA-256 with salt for secure password storage
- [x] **Player Name Support** - Separate display name from username
- [x] **Session Management** - Tokens stored in localStorage, auto-verify on page load
- [x] **Account Tab** - Full UI for login, registration, and profile management
- [x] **User Profile Display** - Shows User ID, Username, Player Name when logged in
- [x] **Unreal Engine Integration** - Special endpoints for game client authentication:
  - `/api/auth/unreal/connect` - Create or retrieve player account by Unreal player ID
  - `/api/auth/unreal/login` - Login with stored credentials
  - Auto-generated passwords for new Unreal players
- [x] **API Key System** - Server-to-server authentication for dedicated game servers
- [x] **Guest Play** - Users can interact without logging in (as "Guest")

### Phase 5: Global Scaling - COMPLETE (Jan 30, 2025)
- [x] Performance optimization for 100+ NPCs
- [x] Connection pooling and caching
- [x] Tiered update system

### Phase 6: Real-Time Communication - COMPLETE (Jan 31, 2025)
- [x] **WebSocket Endpoint** - `/api/ws/game` for low-latency game communication
- [x] **Connection Management** - Track active clients with player IDs
- [x] **Message Router** - Handle ping, npc_action, npc_status, voice_generate, etc.
- [x] **Audio Streaming** - Stream TTS audio in 16KB chunks over WebSocket
- [x] **Event Subscription** - Real-time push events for world, factions, quests, territory
- [x] **Event Broadcaster** - Push updates to subscribed clients
- [x] **WebSocket Proxy** - Backend proxy for external WebSocket connections
- [x] **Updated Documentation** - UNREAL_INTEGRATION_GUIDE.md with WebSocket API details

### Phase 7: Multi-NPC Conversation Groups - COMPLETE (Jan 31, 2025)
- [x] **Location Tracking** - Track NPC and player positions from Unreal Engine (x, y, z, zone)
- [x] **Proximity Detection** - Automatically find NPCs near the player (configurable radius)
- [x] **Group Conversations** - Multiple NPCs participate in same conversation
- [x] **AI Turn Selection** - GPT-5.2 orchestrator determines which NPC responds
- [x] **Response Types** - NPCs can agree, disagree, elaborate, interrupt, or redirect
- [x] **Tension System** - Conversations have dynamic tension levels
- [x] **NPC-to-NPC Reactions** - NPCs respond to each other, not just the player
- [x] **HTTP + WebSocket Support** - Full API available via both protocols
- [x] **Batch Location Updates** - Efficient bulk updates from game engine
- [x] **Voice Output for Groups** - Each NPC speaks with their unique ElevenLabs voice
- [x] **Streamed Voice Audio** - Audio streamed in 16KB chunks for smooth playback
- [x] **Sequential Voice Playback** - NPCs speak in order for natural conversations

---

## API Endpoints

### NPC Management
- `POST /api/npc/init` - Initialize NPC
- `POST /api/npc/action` - Process player action (includes player_id, returns reputation, topics_extracted, topics_remembered, heard_from_others)
- `GET /api/npc/status/{npc_id}` - Get NPC status
- `GET /api/npc/list` - List active NPCs
- `GET /api/npc/relationships/{npc_id}` - Get NPC's social relationships
- `GET /api/npc/memories/{npc_id}/{player_id}` - Get topics NPC remembers about a player
- `POST /api/npc/share-memories/{from_npc}/{to_npc}` - Share memories between NPCs
- `GET /api/npc/heard-about/{npc_id}/{player_id}` - Get secondhand info NPC heard from others

### Memory Decay
- `POST /api/memory/decay?hours=N` - Apply N hours of memory decay
- `GET /api/memory/status` - Get memory strength status (filter by player_id/npc_id)
- `POST /api/memory/cleanup?threshold=0.1` - Remove forgotten memories

### Dynamic Quests
- `POST /api/quest/generate/{npc_id}?player_id=X` - Generate personalized quest
- `GET /api/quests/available` - List available quests
- `POST /api/quest/accept/{quest_id}` - Accept a quest
- `POST /api/quest/complete/{quest_id}` - Complete quest and get rewards

### World Simulation
- `POST /api/world/start?time_scale=N&tick_interval=S` - Start simulation (Nx speed, tick every S seconds)
- `POST /api/world/stop` - Stop simulation
- `GET /api/world/status` - Get simulation status, stats, active NPCs
- `POST /api/world/tick` - Manual tick (for testing)
- `GET /api/world/events` - Get recent world events log

### Factions
- `GET /api/factions` - Get all factions and their status
- `GET /api/faction/{faction_id}` - Get faction details
- `GET /api/faction/relation/{f1}/{f2}` - Get relation between two factions
- `POST /api/faction/event` - Trigger faction event (skirmish, trade_deal, betrayal, alliance)
- `GET /api/faction/events` - Get recent faction events
- `GET /api/player/{id}/factions` - Get player's faction reputations

### Phase 4 - Civilization APIs
- `POST /api/npc/{npc_id}/goal/generate` - Generate autonomous goal for NPC
- `GET /api/npc/{npc_id}/goals` - Get NPC's goals
- `POST /api/goal/{goal_id}/progress` - Update goal progress
- `POST /api/goal/{goal_id}/abandon` - Abandon a goal
- `POST /api/questchain/create/{npc_id}` - Create quest chain
- `GET /api/questchains` - Get available quest chains
- `POST /api/questchain/{chain_id}/start` - Start quest chain
- `POST /api/questchain/{chain_id}/advance` - Advance to next quest
- `POST /api/traderoute/establish` - Establish trade route
- `GET /api/traderoutes` - Get all trade routes
- `POST /api/traderoute/{route_id}/execute` - Execute trade
- `POST /api/traderoute/{route_id}/disrupt` - Disrupt trade route
- `POST /api/traderoute/{route_id}/restore` - Restore trade route
- `GET /api/territory/control` - Get territory control status
- `POST /api/territory/{territory}/battle` - Initiate territorial battle
- `POST /api/battle/{battle_id}/resolve` - Resolve battle
- `GET /api/battles` - Get battle history
- `POST /api/world/advance/{hours}` - Advance world state (for Unreal Engine)

### Voice API Endpoints (Enhanced)
- `GET /api/voice/available` - Get all 21 library voices + cloned voices
- `GET /api/voice/assignments` - Get all NPC voice assignments with fingerprints
- `GET /api/voice/info/{npc_id}` - Get detailed voice info for specific NPC
- `POST /api/voice/assign/{npc_id}` - Assign unique voice based on personality
- `POST /api/voice/generate/{npc_id}` - Generate speech with fingerprint (returns base64 MP3)
- `POST /api/voice/preview` - Preview fingerprint for personality without assigning
- `POST /api/voice/clone/{npc_id}` - Clone custom voice from audio samples
- `DELETE /api/voice/clone/{npc_id}` - Delete cloned voice
- `GET /api/voice/stats` - Get voice system statistics
- `POST /api/voice/reset/{npc_id}` - **NEW** Reset voice assignment for NPC
- `POST /api/voice/reset-all` - **NEW** Reset all voice assignments

### Speech-to-Text API Endpoints (NEW - Jan 30, 2026)
- `POST /api/speech/transcribe` - Transcribe player audio to text (OpenAI Whisper)
- `POST /api/speech/interact/{npc_id}` - Full voice interaction: STT → NPC → TTS

### WebSocket API (NEW - Jan 31, 2025)
**Real-time, low-latency communication for game engines**

- `ws://host/api/ws/game?player_id=X&player_name=Y` - Main WebSocket endpoint
- `GET /api/ws/status` - Get WebSocket connection statistics

**Message Types (Client → Server):**
- `ping` - Keep-alive heartbeat
- `npc_init` - Initialize NPC (returns status or directs to HTTP init)
- `npc_action` - NPC dialogue/action with AI response
- `npc_status` - Get NPC status
- `voice_generate` - Generate TTS with streaming audio chunks
- `speech_transcribe` - STT transcription
- `subscribe_events` - Subscribe to world_events, faction_updates, quest_updates
- `get_factions` - Get all factions
- `get_world_events` - Get recent world events

**Server → Client Push Events (after subscription):**
- `world_event` - Real-time world events
- `faction_update` - Faction changes
- `quest_update` - Quest status changes
- `territory_update` - Territory control changes

### Multi-NPC Conversation Groups API (NEW - Jan 31, 2025)
**Location-based group conversations with AI-driven dynamics**

**Location Tracking:**
- `POST /api/conversation/location/npc/{npc_id}` - Update NPC position (x, y, z, zone)
- `POST /api/conversation/location/player/{player_id}` - Update player position
- `POST /api/conversation/location/batch` - Batch update multiple locations

**Conversation Management:**
- `GET /api/conversation/nearby/{player_id}` - Get NPCs near player
- `POST /api/conversation/start` - Start group conversation with multiple NPCs
- `POST /api/conversation/{group_id}/message` - Send message, get multi-NPC responses
- `POST /api/conversation/{group_id}/add-npc` - Add NPC to conversation
- `POST /api/conversation/{group_id}/remove-npc/{npc_id}` - Remove NPC
- `POST /api/conversation/{group_id}/end` - End conversation
- `GET /api/conversation/{group_id}` - Get conversation state
- `GET /api/conversation/player/{player_id}/active` - Get player's active conversations
- `GET /api/conversation/stats` - System statistics
- `POST /api/conversation/cleanup` - Clean expired conversations

**WebSocket Message Types for Conversations:**
- `update_location` - Update position from Unreal
- `get_nearby_npcs` - Find NPCs in proximity
- `start_conversation` - Start group chat
- `conversation_message` - Send message to group
- `add_npc_to_conversation` / `remove_npc_from_conversation`
- `end_conversation` / `get_conversation`

### Authentication API Endpoints (NEW - Jan 30, 2026)
- `POST /api/auth/register` - Register new web user (returns JWT token)
- `POST /api/auth/login` - Login with username/email + password
- `GET /api/auth/me` - Get current authenticated user info
- `POST /api/auth/verify` - Verify JWT token validity
- `PUT /api/auth/player-name` - Update player display name
- `PUT /api/auth/password` - Change password
- `POST /api/auth/unreal/connect` - **Unreal Engine** player connection (creates or retrieves account)
- `POST /api/auth/unreal/login` - **Unreal Engine** player login with stored credentials
- `POST /api/auth/api-key` - Generate API key for server-to-server auth
- `GET /api/auth/api-key/validate` - Validate API key
- `DELETE /api/auth/api-key/{key_id}` - Revoke API key
- `GET /api/auth/users` - List all users (admin)

### Player Management
- `GET /api/player/{player_id}` - Get player details, reputations, rumors
- `GET /api/players` - List all tracked players

### NPC Generation
- `POST /api/npc/generate/random` - Generate random NPC
- `POST /api/npc/create/custom` - Create custom NPC

### World Systems
- `POST /api/quest/generate/{npc_id}` - Generate quest from NPC
- `GET /api/quests/available` - List available quests
- `GET /api/territory/overview` - Get territorial overview
- `GET /api/factions` - Get faction status

---

## Database Schema

### SQLite (NPC Memory)
- `memories` - NPC memories with strength and type
- `personality_evolution` - Trait changes over time
- `summary_beliefs` - Consolidated beliefs
- `player_sessions` - Player tracking
- `player_npc_reputation` - Player-NPC reputation scores
- `player_actions` - Action history
- `npc_relationships` - NPC-to-NPC relationships
- `rumors` - Gossip content
- `npc_heard_rumors` - What NPCs know
- `conversation_topics` - Player conversation topics (family, goals, fears, secrets, crimes)
- `shared_memories` - **NEW** Secondhand info NPCs shared with each other about players

---

## Testing Status
- Backend: 100% (40/40 tests passed) - including Phase 4 civilization tests
- Frontend: 100% (all features working)
- Test reports: 
  - `/app/test_reports/iteration_1.json` - Phase 3 tests
  - `/app/test_reports/iteration_2.json` - Phase 4 tests

---

## Code Refactoring (Jan 30, 2026)

### Component Structure
The monolithic App.js (1500+ lines) has been refactored into smaller, reusable components:

```
/app/frontend/src/
├── App.js                    # Main app (600 lines, manages state & routing)
├── App.original.js           # Backup of original monolithic version
├── components/
│   ├── ChatPanel.jsx         # NPC chat interface (~140 lines)
│   ├── WorldControls.jsx     # World simulation controls (~140 lines)
│   ├── FactionUI.jsx         # Faction & Territory tab (~280 lines)
│   ├── PlayersTab.jsx        # Player tracking (~150 lines)
│   └── NPCsTab.jsx           # NPC management (~130 lines)
```

### Unreal Engine Integration Documentation
Created comprehensive integration guide: `/app/GAME_ENGINE_INTEGRATION.md`

**Key sections:**
- Quick Start guide with C++ code examples
- Primary endpoint: `POST /api/world/advance/{hours}` for game loop integration
- All API endpoints documented with request/response examples
- Performance considerations and recommended frequencies
- Blueprint integration patterns
- Error handling best practices

---

## Known Issues
- Minor: ESLint warning for useEffect dependency in App.js (non-critical)

## Technical Debt
- ✅ RESOLVED: App.js broken into smaller components (ChatPanel, WorldControls, FactionUI, PlayersTab, NPCsTab)
