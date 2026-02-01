# Fractured Survival - Cognitive NPC System

## Overview
A fully functional, life-like NPC cognitive system featuring autonomous thinking, memory, personality evolution, and emotional responses. Built for Fractured Survival, a post-apocalyptic survival game.

## Architecture

### System Components
```
┌─────────────────────────────────────────────────────────────┐
│                    COGNITIVE NPC SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│  Thread A (Reactive)     │  Thread B (Autonomous)           │
│  - Player perception     │  - Vitals decay (hunger/fatigue) │
│  - Real-time decisions   │  - 300s reflection loop          │
│  - High priority         │  - Background processing         │
├─────────────────────────────────────────────────────────────┤
│                    Thread C (Async IO)                       │
│  - Memory persistence    │  - Delta-log snapshots           │
│  - Non-blocking writes   │  - Trait ledger updates          │
└─────────────────────────────────────────────────────────────┘

Core Modules:
  🧠 Brain (brain.py)         - LLM-powered cognition & decision-making
  💓 Limbic (limbic.py)       - Emotions, vitals, autonomous reflection
  🎯 Meta-Mind (meta_mind.py) - Conflict resolution, trait drift
  💾 Memory Vault (memory_vault.py) - Persistent storage with Delta-Log
```

### Key Features

#### 1. **Double-Pass Cognitive Loop**
- **Internal Monologue**: Hidden thoughts considering personality, memories, vitals
- **Social Filter**: Public dialogue shaped by persona

#### 2. **Personality System**
8 core traits (0.0-1.0 scale):
- Curiosity, Empathy, Aggression, Paranoia
- Discipline, Romanticism, Opportunism, Anxiety

**Trait Plasticity**: Personality evolves based on experiences
- **Sigmoid Soft-Clamp**: Prevents trait extremes (humanity bounds: 0.05-0.95)
- **Delta-Log System**: Records every personality change with reason
- **Inertia**: Traits resist sudden changes (gradual evolution)

#### 3. **Memory & Belief System**
- **Episodic Memory**: Specific events
- **Social Memory**: Relationships and trust
- **Emotional Memory**: Impactful experiences
- **Summary Beliefs**: High-level worldview (updated every 300s)

#### 4. **Biological Constraints (Vitals)**
- **Hunger**: Decays over 4 hours
- **Fatigue**: Decays over 6 hours
- **Override System**: Critical vitals force behavioral changes

#### 5. **Autonomous Reflection**
- Every 300 seconds, NPC reviews last 5 memories
- Generates summary beliefs
- Updates personality traits
- Occurs in background (Thread B)

## Installation & Setup

### Prerequisites
```bash
# Python 3.11+
# pip install requirements
cd /app/npc_system
pip install -r requirements.txt
```

### Environment Setup
```bash
# .env file (already configured)
EMERGENT_LLM_KEY=sk-emergent-cA0272543971dFe1b1
```

## Usage

### Run Step-by-Step Validation

**Step 1: Foundation (IO & Persistence)**
```bash
python3 tests/test_step1.py
```
Validates:
- Database initialization
- Delta-Log system
- Sigmoid soft-clamp (humanity bounds)
- Async IO handler

### Run Full Simulation

```bash
cd /app/npc_system/sim
python3 headless_terminal.py
```

### Interactive Commands
```
>>> You: I wave hello
>>> You: I draw my weapon
>>> You: status          # View Vera's state
>>> You: memories        # View recent memories
>>> You: beliefs         # View summary beliefs
>>> You: personality     # View trait evolution
>>> You: quit            # Exit
```

## Example Interaction

```
>>> You: I approach cautiously, hands visible

[Think Time] 1.8s

─────────────────────────────────────────────────────────────
🧠 INTERNAL THOUGHT (Hidden from Player):
   "Hands visible... that's a good sign. But I've been deceived before.
   My paranoia (0.8) tells me to stay alert. The last attack came from
   'traders' who seemed friendly at first. I'll question their intent."

💬 Vera SAYS:
   "Stop right there. State your name and business."

📊 STATE:
   Intent: Investigate | Urgency: 0.7
   Mood: Wary | Arousal: 0.6
   Hunger: 0.2 | Fatigue: 0.3
─────────────────────────────────────────────────────────────
```

## Technical Implementation

### Step 1: Foundation ✓
- SQLite database with 3 tables (memories, personality_evolution, summary_beliefs)
- Delta-Log system with sigmoid soft-clamp
- Async IO handler (Thread C)
- **Validation**: 100 negative events → trait stays within bounds

### Step 2: Limbic System ✓
- Vitals decay (hunger, fatigue)
- Emotional state (mood, arousal, valence)
- 300s autonomous reflection loop
- Think-time simulation based on arousal

### Step 3: Brain (LLM Integration) ✓
- GPT-5.2 via emergentintegrations
- Structured JSON output (Pydantic-ready)
- Context injection (memories, beliefs, vitals)
- Error handling with fallback responses

### Step 4: CLI Interface ✓
- Headless terminal simulation
- Real-time interaction
- Status monitoring commands
- Graceful shutdown

## File Structure

```
/app/npc_system/
├── core/
│   ├── brain.py           # LLM-powered cognition
│   ├── limbic.py          # Emotions & vitals
│   ├── meta_mind.py       # Conflict resolution
│   └── npc_system.py      # Complete orchestration
├── database/
│   ├── memory_vault.py    # Persistent storage
│   └── memory_vault.db    # SQLite database
├── persona/
│   └── vera_v1.json       # Vera NPC definition
├── sim/
│   └── headless_terminal.py  # CLI interface
├── tests/
│   └── test_step1.py      # Step 1 validation
├── .env                   # Environment variables
└── requirements.txt       # Dependencies
```

## NPC Persona: Vera #001

**Role**: Guarded Gatekeeper at Porto Cobre Gates

**Personality**:
- High Paranoia (0.8) - Distrusts strangers
- High Empathy (0.7) - Cares for genuine survivors
- High Curiosity (0.8) - Observant and analytical
- Low Aggression (0.2) - Defensive, not offensive

**Backstory**: 3 years guarding the gates. Witnessed betrayals and attacks. Trust must be earned through actions.

## Performance Notes

- **LLM Response Time**: 1-3 seconds (cloud-based GPT-5.2)
- **Memory Storage**: Non-blocking async writes
- **Autonomous Loop**: Lightweight background processing
- **Think Time**: Dynamic (0.1s panicked → 2.0s calm)

## Future Integration: Unreal Engine

The system is designed to be **engine-agnostic**. For Unreal Engine integration:

1. **HTTP Bridge**: Unreal sends "World Snapshots" to cognitive service
2. **JSON Contract**: Receives "Cognitive Frames" with intent, dialogue, urgency
3. **Unreal Execution**: Handles animation, movement, voice (no decision-making)

The "Brain" lives independently - allowing upgrades to AI models or graphics without breaking core logic.

## Credits

Built for **Fractured Survival** using:
- Python 3.11
- emergentintegrations (LLM abstraction)
- SQLite (persistence)
- OpenAI GPT-5.2 (cognition)

---

**Status**: ✅ Fully Functional Standalone System
**Next Phase**: Unreal Engine Integration (when ready)
