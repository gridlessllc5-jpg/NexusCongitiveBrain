# Fractured Survival - Neural Command Interface (NCI) Manual

## Overview
The **Neural Command Interface (NCI)** is a high-level administrative dashboard for the *Fractured Survival* cognitive engine. It allows authorized personnel (Game Developers, Narrators, and Admins) to monitor, manipulate, and simulate the post-apocalyptic world's artificial intelligence agents.

This dashboard provides a direct link to the `npc_system` running on the backend, bypassing the game engine to allow for rapid prototyping, debugging, and world orchestration.

## System Modules

### 1. Neural Link (Chat & Interaction)
**Purpose:** Direct cognitive interface with individual NPCs.
- **Cognitive Feed:** View the NPC's internal monologue (`Inner Thoughts`) before they speak.
- **Emotional Telemetry:** Monitor real-time shifts in emotional state (Joy, Fear, Aggression, Trust).
- **Dialogue Input:** Send messages as a player or administrative voice.
- **Memory IO:** See what new topics the NPC has committed to long-term memory during the conversation.

### 2. Bio-Scanner (NPC Status)
**Purpose:** Detailed analysis of NPC physiological and psychological states.
- **Vitals:** Health, Stamina, Hunger, Thirst.
- **Psych Profile:** Current personality traits and deviations.
- **Relationships:** Social graph showing who the NPC knows and their trust levels.
- **Memories:** Searchable database of what the NPC knows about players and the world.

### 3. World Simulator (Global State)
**Purpose:** Control the flow of time and background simulation.
- **Chrono-Controls:** Start, Stop, and Accelerate world time.
- **Event Stream:** Live feed of background events (e.g., "Vera gathered wood", "Rector was attacked").
- **Ticking:** Manually advance simulation ticks for debugging.

### 4. Faction Command (Territory & Trade)
**Purpose:** Strategic overview of the geopolitical landscape.
- **Territory Map:** Control status of key locations (Porto Cobre, Downtown, etc.).
- **Relations Matrix:** Real-time diplomatic status between factions (Guards, Traders, Citizens, Outcasts).
- **Trade Network:** Active trade routes and economic flow.

### 5. Player Registry
**Purpose:** Management of human (or test) subjects in the simulation.
- **Profile:** Player stats and global reputation.
- **Reputation Matrix:** Individual standing with every NPC.

## Visual Interface Guide
The NCI uses a **Holographic Terminal** aesthetic designed for low-light environments.
- **Cyan Accents:** Active systems and healthy status.
- **Red/Amber Alerts:** Critical failures, combat events, or hostility.
- **Scanlines:** Visual artifacting to reduce eye strain and simulate legacy hardware connection.

## Troubleshooting
- **Connection Lost:** Initializing the Neural Link requires the encryption handshake (Login). If bypassed, ensure the backend `websockets` module is active.
- **Blank Feed:** If the holographic display is empty, check the `REACT_APP_BACKEND_URL` configuration in the environment settings.
