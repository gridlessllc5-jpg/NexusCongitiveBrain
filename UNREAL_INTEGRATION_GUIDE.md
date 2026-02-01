# Fractured Survival - Complete System Documentation
## Unreal Engine Integration Guide

**API Base URL:** `https://fracturedsurvival.net/api`

---

# Table of Contents

1. [System Overview](#system-overview)
2. [Authentication](#authentication)
3. [NPC Core System](#npc-core-system)
4. [NPC Cognitive Architecture](#npc-cognitive-architecture)
5. [Memory System](#memory-system)
6. [Voice System (TTS/STT)](#voice-system)
7. [WebSocket API (Real-Time)](#websocket-api-real-time-communication)
8. [Quest System](#quest-system)
9. [Faction System](#faction-system)
10. [World Events](#world-events)
11. [Territory & Battles](#territory--battles)
12. [Trade Routes](#trade-routes)
13. [Zone Management](#zone-management)
14. [Data Models & Structs](#data-models--structs)
15. [Integration Examples](#integration-examples)

---

# System Overview

Fractured Survival is a **cognitive NPC system** for post-apocalyptic game worlds. It provides:

- **AI-Powered NPCs** with persistent memory and personality
- **Double-Pass Cognitive Processing** (reflection → response)
- **Dynamic Quest Generation** based on NPC goals
- **Faction System** with reputation and alliances
- **World Events** that affect all NPCs
- **Territory Control** with faction battles
- **Trade Networks** between NPCs/locations
- **Voice Generation** (unique TTS per NPC)
- **Speech Recognition** (player voice input)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRACTURED SURVIVAL ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   UNREAL ENGINE                         FRACTURED SURVIVAL API           │
│   ─────────────                         ────────────────────             │
│                                                                          │
│   Player Input ─────────────────────▶  /api/npc/action                  │
│                                              │                           │
│                                              ▼                           │
│                                     ┌─────────────────┐                  │
│                                     │ Cognitive Brain │                  │
│                                     │   (GPT-5.2)     │                  │
│                                     └────────┬────────┘                  │
│                                              │                           │
│                                              ▼                           │
│   NPC Dialogue  ◀───────────────────  JSON Response                     │
│   NPC Animation ◀─────────────────── (mood, intent)                     │
│   Voice Audio   ◀────────────────────  /api/voice/generate              │
│                                                                          │
│   ─────────────────────────────────────────────────────────────────     │
│                                                                          │
│   World State   ◀────────────────────  /api/world/events                │
│   Faction Rep   ◀────────────────────  /api/factions                    │
│   Quest Updates ◀────────────────────  /api/quests/available            │
│   Territory Map ◀────────────────────  /api/territory/control           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Authentication

## POST /auth/unreal/login
Primary authentication for Unreal Engine clients.

```json
// REQUEST
{
  "player_id": "unreal_player_001",
  "player_name": "SurvivorJohn"
}

// RESPONSE
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": "usr_abc123",
  "player_name": "SurvivorJohn",
  "is_new_user": false
}
```

## POST /auth/api-key
Create API key for server-to-server communication.

```json
// REQUEST (requires auth token)
{
  "key_name": "UnrealGameServer"
}

// RESPONSE
{
  "api_key": "fsk_...",
  "key_id": "key_abc123"
}
```

---

# NPC Core System

## POST /npc/init
**Initialize an NPC before any interaction.**

```json
// REQUEST
{
  "npc_id": "vera",           // Required: NPC identifier
  "player_id": "player_001"   // Optional: defaults to "default_player"
}

// RESPONSE
{
  "status": "initialized",    // or "already_exists"
  "npc_id": "vera",
  "role": "Guarded Gatekeeper",
  "location": "Porto Cobre Gates"
}
```

## POST /npc/action
**Main interaction endpoint - send player action, get NPC response.**

```json
// REQUEST
{
  "npc_id": "vera",
  "player_id": "player_001",
  "action": "Hello, I need supplies for my group."
}

// RESPONSE
{
  "npc_id": "vera",
  "player_id": "player_001",
  "reflection": "A survivor asking for supplies. Given the recent attacks, I need to be cautious...",
  "dialogue": "Supplies don't come free around here. What do you have to trade?",
  "inner_thoughts": "Could be legitimate, but the last 'trader' tried to rob us...",
  "mood_shift": "Cautious",
  "intent": "Trade",
  "location": "Porto Cobre Gates",
  "emotional_state": {
    "mood": "wary",
    "energy": 0.7,
    "stress": 0.4
  },
  "personality": {
    "friendliness": 0.4,
    "aggression": 0.2,
    "curiosity": 0.8,
    "loyalty": 0.6,
    "discipline": 0.6,
    "romanticism": 0.4,
    "opportunism": 0.5,
    "paranoia": 0.8
  }
}
```

### Intent Values (for animation/behavior)
| Intent | Description | Suggested Animation |
|--------|-------------|---------------------|
| `Investigate` | NPC is curious, examining | Look around, lean forward |
| `Guard` | Defensive stance | Hand on weapon, alert pose |
| `Trade` | Open to negotiation | Relaxed, gesture to goods |
| `Assist` | Wants to help | Approach, open hands |
| `Flee` | Danger detected | Back away, look for exits |
| `Attack` | Hostile action | Combat stance |
| `Socialize` | Friendly chat | Relaxed, smile |
| `Ignore` | Dismissive | Turn away, wave off |

### Mood Values (for facial/body animation)
| Mood | Description |
|------|-------------|
| `neutral` | Default state |
| `wary` | Suspicious, alert |
| `friendly` | Open, positive |
| `hostile` | Aggressive, angry |
| `fearful` | Scared, anxious |
| `curious` | Interested, engaged |
| `sad` | Melancholy, down |

## GET /npc/status/{npc_id}
Get current NPC state without interaction.

```json
// RESPONSE
{
  "npc_id": "vera",
  "status": "active",
  "role": "Guarded Gatekeeper",
  "location": "Porto Cobre Gates",
  "emotional_state": {
    "mood": "neutral",
    "energy": 0.5,
    "stress": 0.3
  },
  "personality": {...},
  "current_goal": "secure_area"
}
```

## GET /npc/list
Get all initialized NPCs.

```json
// RESPONSE
{
  "npcs": ["vera", "marcus", "finn"],
  "count": 3
}
```

## POST /npc/generate/random
Generate a new random NPC with unique personality.

```json
// REQUEST
{
  "name": "CustomNPC",        // Optional - auto-generated if empty
  "role": "Wandering Trader", // Optional
  "location": "Porto Cobre",  // Optional
  "faction": "traders"        // Optional
}

// RESPONSE
{
  "npc_id": "customnpc_12345",
  "name": "CustomNPC",
  "role": "Wandering Trader",
  "gender": "male",
  "location": "Porto Cobre",
  "faction": "traders",
  "personality": {
    "curiosity": 0.6,
    "empathy": 0.5,
    "aggression": 0.3,
    "paranoia": 0.4,
    "discipline": 0.5,
    "romanticism": 0.4,
    "opportunism": 0.7
  },
  "backstory": "Generated backstory based on personality...",
  "dialogue_style": "Friendly but business-focused"
}
```

---

# NPC Cognitive Architecture

## How the AI Brain Works

The NPC brain uses a **Double-Pass** cognitive model:

```
┌─────────────────────────────────────────────────────────────┐
│                    DOUBLE-PASS PROCESSING                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PLAYER INPUT: "I need medicine for my sick child"         │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              PASS 1: REFLECTION                      │   │
│   │                                                      │   │
│   │  1. Retrieve memories about this player              │   │
│   │  2. Check personality traits (empathy: 0.7)          │   │
│   │  3. Consider current mood and stress                 │   │
│   │  4. Evaluate faction relationships                   │   │
│   │  5. Generate internal reflection                     │   │
│   │                                                      │   │
│   │  Output: "This player helped us before. A sick       │   │
│   │  child is serious. My empathy is high, I want to     │   │
│   │  help, but supplies are limited..."                  │   │
│   └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              PASS 2: RESPONSE                        │   │
│   │                                                      │   │
│   │  1. Generate dialogue based on reflection            │   │
│   │  2. Determine intent (Assist, Trade, etc.)           │   │
│   │  3. Calculate mood shift                             │   │
│   │  4. Update emotional state                           │   │
│   │  5. Store memory of interaction                      │   │
│   │                                                      │   │
│   │  Output:                                             │   │
│   │  - dialogue: "A sick child? That's serious..."       │   │
│   │  - intent: "Assist"                                  │   │
│   │  - mood_shift: "Sympathetic"                         │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Personality Traits

Each NPC has persistent personality traits that influence all responses:

```json
{
  "personality": {
    "curiosity": 0.0-1.0,      // How interested in new things
    "empathy": 0.0-1.0,        // Care for others
    "aggression": 0.0-1.0,     // Tendency toward violence
    "paranoia": 0.0-1.0,       // Suspicion/distrust
    "discipline": 0.0-1.0,     // Self-control
    "romanticism": 0.0-1.0,    // Idealism vs pragmatism
    "opportunism": 0.0-1.0,    // Self-interest
    "loyalty": 0.0-1.0,        // Commitment to faction/friends
    "risk_tolerance": 0.0-1.0  // Willingness to take risks
  }
}
```

---

# Memory System

NPCs remember interactions and form opinions over time.

## GET /npc/memories/{npc_id}/{player_id}
Get what an NPC remembers about a player.

```json
// RESPONSE
{
  "npc_id": "vera",
  "player_id": "player_001",
  "memories": [
    {
      "id": "mem_001",
      "memory_type": "episodic",
      "content": "Player helped defend the gates from raiders",
      "strength": 0.9,
      "emotional_valence": 0.8,  // Positive memory
      "timestamp": "2024-01-15T..."
    },
    {
      "id": "mem_002",
      "memory_type": "social",
      "content": "Player asked about my family - seemed genuine",
      "strength": 0.7,
      "emotional_valence": 0.5,
      "timestamp": "2024-01-16T..."
    }
  ],
  "trust_level": 0.6,
  "total_interactions": 5
}
```

## GET /npc/relationships/{npc_id}
Get NPC's relationships with other NPCs.

```json
// RESPONSE
{
  "npc_id": "vera",
  "relationships": {
    "marcus": {
      "trust": 0.8,
      "familiarity": 0.9,
      "last_interaction": "2024-01-14T..."
    },
    "finn": {
      "trust": 0.3,
      "familiarity": 0.5,
      "last_interaction": "2024-01-10T..."
    }
  }
}
```

## POST /npc/gossip/{from_npc}/{to_npc}
Simulate NPCs sharing information about players.

```json
// RESPONSE
{
  "from_npc": "marcus",
  "to_npc": "vera",
  "shared_info": [
    "Player helped with the water purifier",
    "Player is looking for medical supplies"
  ],
  "trust_transfer": 0.1  // Vera now trusts player slightly more
}
```

## POST /memory/decay
Apply time-based memory decay (run periodically).

```json
// REQUEST
{
  "hours": 24.0  // Simulate 24 hours passing
}

// RESPONSE
{
  "memories_decayed": 45,
  "memories_forgotten": 3
}
```

---

# Voice System

## POST /voice/generate/{npc_id}
Generate speech audio for NPC dialogue.

```json
// REQUEST
{
  "text": "State your business, stranger."
}

// RESPONSE
// Content-Type: audio/mpeg
// Body: Binary MP3 audio data
```

## POST /voice/assign/{npc_id}
Assign a unique voice to an NPC.

```json
// RESPONSE
{
  "status": "assigned",
  "npc_id": "vera",
  "voice_id": "EXAVITQu4vr4xnSDxMaL",
  "voice_name": "Sarah",
  "gender": "female"
}
```

## GET /voice/info/{npc_id}
Get voice information for an NPC.

```json
// RESPONSE
{
  "npc_id": "vera",
  "voice_id": "EXAVITQu4vr4xnSDxMaL",
  "voice_name": "Sarah",
  "gender": "female",
  "has_custom_voice": false
}
```

## POST /speech/transcribe
Convert player voice to text.

```json
// REQUEST
{
  "audio_base64": "base64_encoded_audio_data",
  "language": "en"  // Optional, default: "en"
}

// RESPONSE
{
  "text": "I need help finding medicine",
  "language": "en",
  "confidence": 0.95
}
```

**Supported Audio Formats:** mp3, mp4, mpeg, mpga, m4a, wav, webm

## POST /speech/interact/{npc_id}
Complete voice interaction: STT → NPC Response → TTS

```json
// REQUEST
{
  "audio_base64": "base64_encoded_player_audio",
  "player_id": "player_001"
}

// RESPONSE
{
  "player_text": "Hello, can you help me?",
  "npc_response": {
    "dialogue": "Depends on what kind of help you need...",
    "mood_shift": "Curious",
    "intent": "Investigate"
  },
  "audio_base64": "base64_encoded_npc_audio"
}
```

---

# WebSocket API (Real-Time Communication)

The WebSocket API provides **low-latency, bidirectional communication** for real-time game interactions. This is the recommended approach for Unreal Engine integration as it eliminates HTTP overhead.

## Connection

**WebSocket URL:** `ws://{host}/api/ws/game?player_id={id}&player_name={name}`

### Connection Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| player_id | string | Unique player identifier |
| player_name | string | Player display name |

### Connection Example (Unreal Engine C++)
```cpp
// Use UE5's WebSocket support
#include "WebSocketsModule.h"
#include "IWebSocket.h"

// Create WebSocket
TSharedPtr<IWebSocket> WebSocket = FWebSocketsModule::Get().CreateWebSocket(
    TEXT("ws://api.fracturedsurvival.net/api/ws/game?player_id=player123&player_name=Hunter")
);

// Connect callbacks
WebSocket->OnConnected().AddLambda([]() {
    UE_LOG(LogTemp, Log, TEXT("Connected to NPC WebSocket!"));
});

WebSocket->OnMessage().AddLambda([](const FString& Message) {
    // Parse JSON response
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    FJsonSerializer::Deserialize(Reader, JsonObject);
    
    FString Type = JsonObject->GetStringField("type");
    if (Type == "npc_response") {
        FString Dialogue = JsonObject->GetStringField("dialogue");
        // Display dialogue in game
    }
});

WebSocket->Connect();
```

### Connection Response
When connected, the server sends:
```json
{
  "type": "connected",
  "player_id": "player123",
  "player_name": "Hunter",
  "active_npcs": ["vera", "merchant", "guard"],
  "message": "Connected to Fractured Survival NPC Service",
  "timestamp": 1234567890.123
}
```

---

## Message Types

### Client → Server Messages

#### 1. Ping (Keep-Alive)
```json
{
  "type": "ping",
  "request_id": "ping_001"
}
```
Response:
```json
{
  "type": "pong",
  "timestamp": 1234567890.123,
  "request_id": "ping_001"
}
```

#### 2. NPC Action (Dialogue)
```json
{
  "type": "npc_action",
  "npc_id": "vera",
  "action": "Hello, I'm looking for supplies",
  "request_id": "action_001"
}
```
Response:
```json
{
  "type": "npc_response",
  "npc_id": "vera",
  "player_id": "player123",
  "dialogue": "State your business, traveler. What supplies do you need?",
  "inner_thoughts": "Another stranger seeking resources...",
  "intent": "Investigate",
  "emotional_state": "Wary",
  "urgency": 0.7,
  "limbic_state": {
    "vitals": {"hunger": 0.3, "fatigue": 0.2},
    "emotional_state": {"mood": "Suspicious", "arousal": 0.6}
  },
  "timestamp": 1234567890.123,
  "request_id": "action_001"
}
```

#### 3. NPC Status
```json
{
  "type": "npc_status",
  "npc_id": "vera",
  "request_id": "status_001"
}
```
Response:
```json
{
  "type": "npc_status_response",
  "npc_id": "vera",
  "status": "active",
  "role": "Guarded Gatekeeper",
  "location": "Porto Cobre Gates",
  "emotional_state": {"mood": "Neutral"},
  "timestamp": 1234567890.123,
  "request_id": "status_001"
}
```

#### 4. Voice Generation (Streamed Audio)
```json
{
  "type": "voice_generate",
  "npc_id": "vera",
  "text": "Welcome to Porto Cobre, traveler.",
  "mood": "neutral",
  "format": "wav",
  "request_id": "voice_001"
}
```
Response (multiple messages):
```json
// First, audio chunks are streamed:
{
  "type": "voice_chunk",
  "npc_id": "vera",
  "chunk_index": 0,
  "total_chunks": 4,
  "audio_data": "base64_encoded_audio_chunk",
  "format": "wav",
  "request_id": "voice_001"
}
// ... more chunks ...

// Finally, completion message:
{
  "type": "voice_complete",
  "npc_id": "vera",
  "text": "Welcome to Porto Cobre, traveler.",
  "format": "wav",
  "total_size": 51035,
  "request_id": "voice_001"
}
```

#### 5. Speech Transcription (STT)
```json
{
  "type": "speech_transcribe",
  "audio_base64": "base64_encoded_audio",
  "language": "en",
  "request_id": "stt_001"
}
```
Response:
```json
{
  "type": "transcription",
  "text": "I need to find supplies",
  "language": "en",
  "timestamp": 1234567890.123,
  "request_id": "stt_001"
}
```

#### 6. Subscribe to Events
```json
{
  "type": "subscribe_events",
  "events": ["world_events", "faction_updates", "quest_updates"],
  "request_id": "sub_001"
}
```
Response:
```json
{
  "type": "subscribed",
  "events": ["world_events", "faction_updates", "quest_updates"],
  "timestamp": 1234567890.123,
  "request_id": "sub_001"
}
```

#### 7. Get Factions
```json
{
  "type": "get_factions",
  "request_id": "factions_001"
}
```

#### 8. Get World Events
```json
{
  "type": "get_world_events",
  "limit": 10,
  "request_id": "events_001"
}
```

---

### Server → Client Push Events (After Subscription)

When subscribed, you'll receive real-time events:

```json
// World Event
{
  "type": "world_event",
  "event": {
    "type": "RAID",
    "detail": "Raiders spotted near the eastern border"
  },
  "timestamp": 1234567890.123
}

// Faction Update
{
  "type": "faction_update",
  "faction_id": "traders",
  "update": {
    "power_change": -5,
    "reason": "Lost trade route"
  },
  "timestamp": 1234567890.123
}

// Quest Update
{
  "type": "quest_update",
  "quest_id": "quest_001",
  "update": {
    "status": "completed",
    "rewards_given": true
  },
  "timestamp": 1234567890.123
}
```

---

## Unreal Engine Integration Pattern

### 1. WebSocket Manager Component
```cpp
UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class FRACTUREDSURVIVAL_API UFSWebSocketManager : public UActorComponent
{
    GENERATED_BODY()
    
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString ServerURL;
    
    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString PlayerID;
    
    UFUNCTION(BlueprintCallable)
    void Connect();
    
    UFUNCTION(BlueprintCallable)
    void SendNPCAction(const FString& NPCId, const FString& Action);
    
    UFUNCTION(BlueprintCallable)
    void RequestVoice(const FString& NPCId, const FString& Text, const FString& Mood);
    
    DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnNPCResponse, const FNPCResponse&, Response);
    UPROPERTY(BlueprintAssignable)
    FOnNPCResponse OnNPCResponse;
    
    DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnVoiceChunk, int32, ChunkIndex, const TArray<uint8>&, AudioData);
    UPROPERTY(BlueprintAssignable)
    FOnVoiceChunk OnVoiceChunk;
    
private:
    TSharedPtr<IWebSocket> WebSocket;
    TArray<uint8> AudioBuffer;  // For accumulating voice chunks
};
```

### 2. Handling Voice Audio Streaming
```cpp
void UFSWebSocketManager::OnMessage(const FString& Message)
{
    TSharedPtr<FJsonObject> Json;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    FJsonSerializer::Deserialize(Reader, Json);
    
    FString Type = Json->GetStringField("type");
    
    if (Type == "voice_chunk")
    {
        // Decode base64 audio chunk
        FString AudioB64 = Json->GetStringField("audio_data");
        TArray<uint8> ChunkData;
        FBase64::Decode(AudioB64, ChunkData);
        
        // Append to buffer
        AudioBuffer.Append(ChunkData);
        
        // Broadcast chunk received
        int32 ChunkIndex = Json->GetIntegerField("chunk_index");
        OnVoiceChunk.Broadcast(ChunkIndex, ChunkData);
    }
    else if (Type == "voice_complete")
    {
        // All chunks received - play audio
        PlayAccumulatedAudio();
        AudioBuffer.Empty();
    }
}

void UFSWebSocketManager::PlayAccumulatedAudio()
{
    // Create sound wave from buffer
    USoundWave* SoundWave = NewObject<USoundWave>();
    // ... configure and play audio
}
```

### 3. Blueprint Integration
The WebSocket Manager can be used directly in Blueprints:
1. Add `FSWebSocketManager` component to your Player Controller
2. Set `ServerURL` and `PlayerID` 
3. Call `Connect()` on BeginPlay
4. Bind to `OnNPCResponse` and `OnVoiceChunk` events
5. Call `SendNPCAction()` when player interacts with NPC

---

## WebSocket Status Endpoint

**GET /api/ws/status**

Check current WebSocket connection statistics:

```json
{
  "active_connections": 12,
  "event_subscribers": {
    "world_events": 8,
    "faction_updates": 5,
    "territory_updates": 3,
    "quest_updates": 10
  },
  "handler_ready": true
}
```

---

# Multi-NPC Conversation Groups

The conversation groups system enables **realistic group conversations** where multiple NPCs can participate together, responding to the player AND to each other based on their personalities and relationships.

## Key Features

- **Location-Based Grouping**: NPCs automatically discovered based on proximity from Unreal Engine position data
- **AI-Driven Turn Selection**: GPT-5.2 orchestrates who speaks next based on context
- **Dynamic Response Types**: NPCs can agree, disagree, elaborate, interrupt, or redirect conversations
- **Tension System**: Conversations have dynamic tension levels that affect NPC behavior
- **NPC-to-NPC Reactions**: NPCs respond to each other, creating natural group dynamics

---

## Location Tracking

Before starting conversations, update NPC and player positions from Unreal Engine.

### POST /api/conversation/location/npc/{npc_id}
Update NPC position in the world.

```cpp
// Unreal Engine C++ - Update NPC Location
void AMyNPCActor::Tick(float DeltaTime)
{
    FVector Location = GetActorLocation();
    
    FString Payload = FString::Printf(
        TEXT("{\"x\": %f, \"y\": %f, \"z\": %f, \"zone\": \"%s\"}"),
        Location.X, Location.Y, Location.Z, *CurrentZone
    );
    
    // Send to API
    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(FString::Printf(TEXT("%s/api/conversation/location/npc/%s"), *APIBaseURL, *NPCId));
    Request->SetVerb("POST");
    Request->SetContentAsString(Payload);
    Request->ProcessRequest();
}
```

### POST /api/conversation/location/player/{player_id}
Update player position.

```json
// REQUEST
{
  "x": 1250.5,
  "y": -340.2,
  "z": 100.0,
  "zone": "market_square"
}

// RESPONSE
{
  "status": "updated",
  "player_id": "player_123",
  "location": {"x": 1250.5, "y": -340.2, "z": 100.0, "zone": "market_square"}
}
```

### POST /api/conversation/location/batch
Batch update multiple locations efficiently.

```json
// REQUEST
[
  {"id": "player_123", "type": "player", "x": 100, "y": 200, "z": 0, "zone": "market"},
  {"id": "vera", "type": "npc", "x": 120, "y": 210, "z": 0, "zone": "market"},
  {"id": "marcus", "type": "npc", "x": 90, "y": 190, "z": 0, "zone": "market"}
]

// RESPONSE
{"status": "batch_updated", "count": 3}
```

---

## Finding Nearby NPCs

### GET /api/conversation/nearby/{player_id}
Get NPCs within proximity of the player.

```json
// GET /api/conversation/nearby/player_123?max_distance=500

// RESPONSE
{
  "player_id": "player_123",
  "nearby_npcs": [
    {
      "npc_id": "vera",
      "name": "Vera",
      "role": "Guarded Gatekeeper",
      "location": {"x": 120, "y": 210, "z": 0, "zone": "market_square"}
    },
    {
      "npc_id": "marcus",
      "name": "Marcus",
      "role": "Patrol Leader",
      "location": {"x": 90, "y": 190, "z": 0, "zone": "market_square"}
    }
  ],
  "count": 2
}
```

---

## Starting Group Conversations

### POST /api/conversation/start
Start a multi-NPC conversation.

```json
// REQUEST
{
  "player_id": "player_123",
  "player_name": "Survivor",
  "npc_ids": ["vera", "marcus"],  // Optional: specify NPCs or auto-discover
  "location": "market_square",
  "auto_discover": false          // Set true to use nearby NPCs automatically
}

// RESPONSE
{
  "status": "started",
  "group_id": "conv_abc123",
  "location": "market_square",
  "participants": [
    {"npc_id": "vera", "name": "Vera", "role": "Guarded Gatekeeper", "mood": "Wary"},
    {"npc_id": "marcus", "name": "Marcus", "role": "Patrol Leader", "mood": "Alert"}
  ],
  "message": "Group conversation started with 2 NPCs"
}
```

---

## Sending Messages

### POST /api/conversation/{group_id}/message
Send a message and receive responses from multiple NPCs.

```json
// REQUEST
{
  "message": "Have you heard anything about raiders in the area?",
  "target_npc_id": null  // Optional: direct message to specific NPC
}

// RESPONSE
{
  "status": "processed",
  "group_id": "conv_abc123",
  "responses": [
    {
      "npc_id": "vera",
      "npc_name": "Vera",
      "dialogue": "Word on the street is they've been sniffing around the eastern perimeter...",
      "response_type": "direct_reply",
      "target": "player",
      "mood": "Cautious",
      "inner_thoughts": "Should I tell them everything I know?"
    },
    {
      "npc_id": "marcus",
      "npc_name": "Marcus",
      "dialogue": "Vera's right. My patrol spotted fresh tracks two nights ago. Not random scavengers either.",
      "response_type": "agreement",
      "target": "vera",
      "mood": "Alert",
      "inner_thoughts": "If Vera's worried, we should all be worried."
    }
  ],
  "response_count": 2,
  "tension_level": 0.3,
  "topic": "security"
}
```

### Response Types

NPCs respond with different types based on AI orchestration:

| Type | Description |
|------|-------------|
| `direct_reply` | Responding directly to the player |
| `agreement` | Agreeing with another NPC's statement |
| `disagreement` | Disagreeing with another NPC |
| `elaboration` | Adding more detail to another NPC's point |
| `interruption` | Urgently interjecting into the conversation |
| `redirect` | Changing the topic to something more important |
| `silent` | Choosing not to speak (filtered from response) |

---

## Managing Conversations

### POST /api/conversation/{group_id}/add-npc
Add an NPC who walks into the conversation area.

```json
// REQUEST
{"npc_id": "elena"}

// RESPONSE
{
  "status": "added",
  "group_id": "conv_abc123",
  "npc_id": "elena",
  "total_participants": 3
}
```

### POST /api/conversation/{group_id}/remove-npc/{npc_id}
Remove an NPC who leaves the area.

### POST /api/conversation/{group_id}/end
End the conversation.

```json
// RESPONSE
{
  "status": "ended",
  "group_id": "conv_abc123",
  "duration_seconds": 45.2,
  "total_messages": 8,
  "final_tension": 0.4
}
```

### GET /api/conversation/{group_id}
Get full conversation state including history.

---

## WebSocket Integration

All conversation group operations are also available via WebSocket for real-time use.

### Starting via WebSocket
```json
// Send
{
  "type": "start_conversation",
  "npc_ids": ["vera", "marcus"],
  "location": "trading_post",
  "auto_discover": false
}

// Receive
{
  "type": "conversation_started",
  "group_id": "conv_xyz789",
  "participants": [...]
}
```

### Sending Messages via WebSocket
```json
// Send
{
  "type": "conversation_message",
  "group_id": "conv_xyz789",
  "message": "What's happening at the old factory?",
  "target_npc_id": "vera"
}

// Receive
{
  "type": "conversation_responses",
  "group_id": "conv_xyz789",
  "responses": [...],
  "tension_level": 0.2
}
```

### Real-Time Location Updates
```json
// Send from Unreal Engine tick
{
  "type": "update_location",
  "entity_type": "player",
  "entity_id": "player_123",
  "x": 1250.5,
  "y": -340.2,
  "z": 100.0,
  "zone": "market"
}
```

---

## Unreal Engine Integration Pattern

### Conversation Manager Component

```cpp
UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class FRACTUREDSURVIVAL_API UConversationManager : public UActorComponent
{
    GENERATED_BODY()

public:
    // Current conversation group ID
    UPROPERTY(BlueprintReadOnly)
    FString ActiveGroupId;
    
    // Start conversation with nearby NPCs
    UFUNCTION(BlueprintCallable)
    void StartGroupConversation(const TArray<FString>& NPCIds, const FString& Location);
    
    // Send message to the group
    UFUNCTION(BlueprintCallable)
    void SendGroupMessage(const FString& Message, const FString& TargetNPCId = "");
    
    // Callbacks for UI
    DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnNPCResponses, const TArray<FNPCDialogueResponse>&, Responses);
    UPROPERTY(BlueprintAssignable)
    FOnNPCResponses OnNPCResponses;
    
    // Update player location (call from PlayerController tick)
    UFUNCTION(BlueprintCallable)
    void UpdatePlayerLocation(FVector Location, const FString& Zone);
};

// Implementation
void UConversationManager::SendGroupMessage(const FString& Message, const FString& TargetNPCId)
{
    TSharedRef<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField("type", "conversation_message");
    JsonObject->SetStringField("group_id", ActiveGroupId);
    JsonObject->SetStringField("message", Message);
    if (!TargetNPCId.IsEmpty())
    {
        JsonObject->SetStringField("target_npc_id", TargetNPCId);
    }
    
    FString OutputString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
    FJsonSerializer::Serialize(JsonObject, Writer);
    
    WebSocket->Send(OutputString);
}
```

### Blueprint Usage

1. Add `UConversationManager` to your Player Controller
2. Call `UpdatePlayerLocation()` every tick or on significant movement
3. When player approaches NPCs, call `StartGroupConversation()`
4. Bind to `OnNPCResponses` to display dialogue UI
5. Call `SendGroupMessage()` when player chooses dialogue option

---

# Quest System

## POST /quest/generate/{npc_id}
Generate a dynamic quest based on NPC's current state.

```json
// RESPONSE
{
  "quest_id": "quest_vera_001",
  "quest_type": "fetch",
  "title": "Medical Supply Run",
  "description": "Vera needs antibiotics from the old hospital",
  "giver_npc": "vera",
  "objectives": [
    {
      "id": "obj_001",
      "description": "Find antibiotics in the hospital",
      "type": "collect",
      "target": "antibiotics",
      "quantity": 3,
      "completed": false
    },
    {
      "id": "obj_002", 
      "description": "Return to Vera",
      "type": "deliver",
      "target": "vera",
      "completed": false
    }
  ],
  "rewards": {
    "reputation": 0.1,
    "items": ["water_purifier"],
    "trust_gain": 0.15
  },
  "difficulty": "medium",
  "time_limit": null,
  "expires_at": "2024-01-20T..."
}
```

### Quest Types
| Type | Description |
|------|-------------|
| `fetch` | Collect items and return |
| `combat` | Eliminate threats |
| `trade` | Negotiate deals |
| `investigate` | Gather information |
| `escort` | Protect someone/something |
| `delivery` | Transport goods |

## GET /quests/available
Get all available quests.

```json
// RESPONSE
{
  "quests": [
    {
      "quest_id": "quest_vera_001",
      "title": "Medical Supply Run",
      "giver_npc": "vera",
      "quest_type": "fetch",
      "difficulty": "medium",
      "status": "available"
    }
  ],
  "count": 1
}
```

## POST /quest/accept/{quest_id}
Accept a quest.

```json
// REQUEST
{
  "player_id": "player_001"
}

// RESPONSE
{
  "status": "accepted",
  "quest_id": "quest_vera_001",
  "started_at": "2024-01-15T..."
}
```

## POST /quest/complete/{quest_id}
Mark quest as complete.

```json
// RESPONSE
{
  "status": "completed",
  "quest_id": "quest_vera_001",
  "rewards_given": {
    "reputation": 0.1,
    "items": ["water_purifier"],
    "trust_gain": 0.15
  },
  "npc_reaction": "Vera is grateful and trusts you more"
}
```

---

# Faction System

## Available Factions

| Faction ID | Name | Description |
|------------|------|-------------|
| `survivors` | The Survivors | Regular people trying to survive |
| `raiders` | The Raiders | Aggressive scavengers |
| `traders` | Merchant Guild | Trade network operators |
| `militia` | Porto Militia | Settlement defenders |
| `scientists` | The Remnant | Pre-war knowledge seekers |

## GET /factions
Get all factions and their current status.

```json
// RESPONSE
{
  "factions": [
    {
      "faction_id": "survivors",
      "name": "The Survivors",
      "description": "Regular people trying to survive",
      "territory_count": 3,
      "member_count": 45,
      "strength": 0.6,
      "morale": 0.7
    },
    {
      "faction_id": "raiders",
      "name": "The Raiders",
      "description": "Aggressive scavengers",
      "territory_count": 2,
      "member_count": 30,
      "strength": 0.8,
      "morale": 0.5
    }
  ]
}
```

## GET /faction/{faction_id}
Get detailed faction information.

```json
// RESPONSE
{
  "faction_id": "survivors",
  "name": "The Survivors",
  "description": "Regular people trying to survive",
  "territories": ["Porto Cobre", "Old Town", "Market Square"],
  "allies": ["traders"],
  "enemies": ["raiders"],
  "neutral": ["militia", "scientists"],
  "resources": {
    "food": 0.6,
    "water": 0.7,
    "weapons": 0.4,
    "medicine": 0.3
  },
  "recent_events": [
    "Successfully defended Porto Cobre from raiders",
    "Established trade agreement with Merchant Guild"
  ]
}
```

## GET /faction/relation/{faction1}/{faction2}
Get relationship between two factions.

```json
// RESPONSE
{
  "faction1": "survivors",
  "faction2": "raiders",
  "relation_value": -0.8,  // -1.0 to 1.0 scale
  "status": "hostile",      // hostile, unfriendly, neutral, friendly, allied
  "recent_events": [
    "Raiders attacked Porto Cobre",
    "Survivors killed raider scouts"
  ],
  "can_improve": true,
  "improvement_requirements": [
    "Return stolen supplies",
    "Release captured raiders"
  ]
}
```

## GET /player/{player_id}/factions
Get player's reputation with all factions.

```json
// RESPONSE
{
  "player_id": "player_001",
  "factions": {
    "survivors": {
      "reputation": 0.6,
      "standing": "friendly",
      "title": "Trusted Ally"
    },
    "raiders": {
      "reputation": -0.3,
      "standing": "unfriendly",
      "title": "Enemy"
    },
    "traders": {
      "reputation": 0.2,
      "standing": "neutral",
      "title": "Customer"
    }
  }
}
```

## POST /player/{player_id}/faction/{faction_id}
Modify player's faction reputation.

```json
// REQUEST
{
  "change": 0.1,  // -1.0 to 1.0
  "reason": "Helped defend settlement"
}

// RESPONSE
{
  "player_id": "player_001",
  "faction_id": "survivors",
  "old_reputation": 0.5,
  "new_reputation": 0.6,
  "standing_change": null,  // or "promoted" / "demoted"
  "ripple_effects": {
    "raiders": -0.05  // Helping survivors angers raiders
  }
}
```

## POST /faction/event
Trigger a faction event.

```json
// REQUEST
{
  "event_type": "skirmish",  // skirmish, alliance, betrayal, trade_deal
  "factions": ["survivors", "raiders"],
  "description": "Raiders ambushed a survivor patrol"
}

// RESPONSE
{
  "event_id": "evt_001",
  "event_type": "skirmish",
  "factions_involved": ["survivors", "raiders"],
  "effects": {
    "survivors": {
      "morale": -0.1,
      "strength": -0.05
    },
    "raiders": {
      "morale": 0.1,
      "reputation_change": -0.1  // More hated
    }
  },
  "world_impact": "Tensions escalate in Porto Cobre region"
}
```

### Faction Event Types
| Event Type | Description |
|------------|-------------|
| `skirmish` | Small combat encounter |
| `battle` | Major territorial conflict |
| `alliance` | Factions become allies |
| `betrayal` | Alliance broken |
| `trade_deal` | Economic agreement |
| `ceasefire` | Temporary peace |
| `declaration_of_war` | Open hostility begins |
| `resource_shortage` | Faction loses resources |
| `leader_change` | New faction leader |

---

# World Events

## GET /world/events
Get recent world events.

```json
// RESPONSE
{
  "events": [
    {
      "event_id": "world_evt_001",
      "timestamp": "2024-01-15T10:30:00Z",
      "event_type": "faction_conflict",
      "title": "Raiders Attack Porto Cobre",
      "description": "A raider war party attacked the eastern gate",
      "factions_involved": ["raiders", "survivors"],
      "location": "Porto Cobre Gates",
      "outcome": "Survivors defended successfully",
      "world_effects": {
        "faction_relations": {
          "survivors_raiders": -0.1
        },
        "territory_changes": null,
        "npc_mood_shift": {
          "vera": "stressed",
          "marcus": "angry"
        }
      }
    }
  ],
  "total_events": 15
}
```

## GET /world/status
Get current world simulation status.

```json
// RESPONSE
{
  "simulation_running": true,
  "world_time": "Day 45, 14:30",
  "time_scale": 1.0,
  "active_conflicts": 2,
  "pending_events": 3,
  "faction_tensions": {
    "survivors_raiders": "high",
    "traders_militia": "low"
  },
  "resource_scarcity": {
    "food": "moderate",
    "water": "low",
    "medicine": "critical"
  }
}
```

## POST /world/tick
Manually advance world state (triggers events, decay, etc.).

```json
// RESPONSE
{
  "tick_completed": true,
  "events_triggered": [
    "Resource shortage in Old Town",
    "Trader caravan arrived"
  ],
  "npcs_updated": 12,
  "memories_decayed": 45
}
```

## POST /world/advance/{hours}
Advance world time by specified hours.

```json
// REQUEST: POST /world/advance/24

// RESPONSE
{
  "hours_advanced": 24,
  "events_occurred": [
    {
      "event_type": "trade_route_completed",
      "description": "Caravan from North reached Porto Cobre"
    },
    {
      "event_type": "resource_depleted",
      "description": "Water reserves running low"
    }
  ],
  "faction_changes": {
    "survivors": {
      "morale": -0.05,
      "resources": {"water": -0.1}
    }
  },
  "npc_changes": {
    "vera": {"stress": 0.1},
    "marcus": {"fatigue": 0.2}
  }
}
```

---

# Territory & Battles

## GET /territory/control
Get current territory control map.

```json
// RESPONSE
{
  "territories": [
    {
      "territory_id": "porto_cobre",
      "name": "Porto Cobre",
      "controlling_faction": "survivors",
      "control_strength": 0.8,
      "contested": false,
      "resources": ["water", "shelter"],
      "strategic_value": 0.9
    },
    {
      "territory_id": "old_hospital",
      "name": "Old Hospital",
      "controlling_faction": "raiders",
      "control_strength": 0.6,
      "contested": true,
      "resources": ["medicine"],
      "strategic_value": 0.7
    }
  ]
}
```

## GET /territory/overview
Get territorial overview with all regions.

```json
// RESPONSE
{
  "total_territories": 8,
  "faction_control": {
    "survivors": 3,
    "raiders": 2,
    "traders": 1,
    "militia": 1,
    "contested": 1
  },
  "hotspots": [
    {
      "territory": "Old Hospital",
      "tension_level": "high",
      "likely_conflict": true
    }
  ]
}
```

## POST /territory/{territory}/battle
Initiate a territorial battle.

```json
// REQUEST
{
  "attacker_faction": "raiders"
}

// RESPONSE
{
  "battle_id": "battle_001",
  "territory": "porto_cobre",
  "attacker": "raiders",
  "defender": "survivors",
  "attacker_strength": 0.7,
  "defender_strength": 0.8,
  "status": "in_progress",
  "estimated_duration": "2 hours"
}
```

## POST /battle/{battle_id}/resolve
Resolve an ongoing battle.

```json
// RESPONSE
{
  "battle_id": "battle_001",
  "winner": "survivors",
  "territory": "porto_cobre",
  "territory_changed_hands": false,
  "casualties": {
    "raiders": 0.2,      // 20% strength lost
    "survivors": 0.1     // 10% strength lost
  },
  "morale_effects": {
    "raiders": -0.15,
    "survivors": 0.1
  },
  "world_event_generated": "Survivors successfully defend Porto Cobre"
}
```

## GET /battles
Get battle history.

```json
// RESPONSE
{
  "battles": [
    {
      "battle_id": "battle_001",
      "territory": "porto_cobre",
      "attacker": "raiders",
      "defender": "survivors",
      "winner": "survivors",
      "timestamp": "2024-01-15T...",
      "duration_hours": 2.5
    }
  ]
}
```

---

# Trade Routes

## GET /traderoutes
Get all trade routes.

```json
// RESPONSE
{
  "routes": [
    {
      "route_id": "route_001",
      "from_location": "Porto Cobre",
      "to_location": "Market Square",
      "from_npc": "vera",
      "to_npc": "marcus",
      "goods": ["water", "food"],
      "status": "active",
      "risk_level": 0.3,
      "last_trade": "2024-01-14T..."
    }
  ]
}
```

## POST /traderoute/establish
Create a new trade route.

```json
// REQUEST
{
  "from_npc": "vera",
  "to_npc": "marcus",
  "from_location": "Porto Cobre",
  "to_location": "Market Square"
}

// RESPONSE
{
  "route_id": "route_002",
  "status": "established",
  "estimated_profit": 0.2,
  "risk_assessment": "low"
}
```

## POST /traderoute/{route_id}/execute
Execute a trade on a route.

```json
// RESPONSE
{
  "route_id": "route_001",
  "trade_completed": true,
  "goods_transferred": ["water x5", "food x3"],
  "profit": 0.15,
  "both_parties_satisfied": true,
  "relationship_bonus": 0.05
}
```

## POST /traderoute/{route_id}/disrupt
Disrupt a trade route (e.g., by raiders).

```json
// REQUEST
{
  "reason": "raider_attack"
}

// RESPONSE
{
  "route_id": "route_001",
  "status": "disrupted",
  "goods_lost": ["water x2"],
  "faction_effects": {
    "traders": {"reputation": -0.1},
    "raiders": {"reputation": -0.05}
  }
}
```

---

# Zone Management

For large-scale games with many NPCs, use zones to optimize processing.

## POST /zone/{zone_id}/register
Register an NPC to a zone for optimized updates.

```json
// REQUEST
{
  "npc_id": "vera"
}

// RESPONSE
{
  "zone_id": "porto_cobre",
  "npc_id": "vera",
  "registered": true,
  "zone_npc_count": 5
}
```

## POST /zone/{zone_id}/tick
Process only NPCs in a specific zone (performance optimization).

```json
// RESPONSE
{
  "zone_id": "porto_cobre",
  "npcs_processed": 5,
  "events_generated": 1,
  "processing_time_ms": 150
}
```

---

# Data Models & Structs

## For Unreal Engine C++

```cpp
// Emotional State
USTRUCT(BlueprintType)
struct FEmotionalState
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite)
    FString Mood;  // "neutral", "wary", "friendly", etc.
    
    UPROPERTY(BlueprintReadWrite)
    float Energy;  // 0.0 - 1.0
    
    UPROPERTY(BlueprintReadWrite)
    float Stress;  // 0.0 - 1.0
};

// Personality
USTRUCT(BlueprintType)
struct FNPCPersonality
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite) float Friendliness;
    UPROPERTY(BlueprintReadWrite) float Aggression;
    UPROPERTY(BlueprintReadWrite) float Curiosity;
    UPROPERTY(BlueprintReadWrite) float Loyalty;
    UPROPERTY(BlueprintReadWrite) float Discipline;
    UPROPERTY(BlueprintReadWrite) float Romanticism;
    UPROPERTY(BlueprintReadWrite) float Opportunism;
    UPROPERTY(BlueprintReadWrite) float Paranoia;
};

// NPC Response (from /npc/action)
USTRUCT(BlueprintType)
struct FNPCResponse
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite) FString NpcId;
    UPROPERTY(BlueprintReadWrite) FString Dialogue;
    UPROPERTY(BlueprintReadWrite) FString InnerThoughts;
    UPROPERTY(BlueprintReadWrite) FString MoodShift;
    UPROPERTY(BlueprintReadWrite) FString Intent;
    UPROPERTY(BlueprintReadWrite) FString Location;
    UPROPERTY(BlueprintReadWrite) FEmotionalState EmotionalState;
    UPROPERTY(BlueprintReadWrite) FNPCPersonality Personality;
};

// Quest
USTRUCT(BlueprintType)
struct FQuest
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite) FString QuestId;
    UPROPERTY(BlueprintReadWrite) FString Title;
    UPROPERTY(BlueprintReadWrite) FString Description;
    UPROPERTY(BlueprintReadWrite) FString QuestType;
    UPROPERTY(BlueprintReadWrite) FString GiverNpc;
    UPROPERTY(BlueprintReadWrite) FString Difficulty;
    UPROPERTY(BlueprintReadWrite) TArray<FQuestObjective> Objectives;
};

// Faction Reputation
USTRUCT(BlueprintType)
struct FFactionReputation
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite) FString FactionId;
    UPROPERTY(BlueprintReadWrite) float Reputation;  // -1.0 to 1.0
    UPROPERTY(BlueprintReadWrite) FString Standing;  // "hostile", "neutral", "friendly"
    UPROPERTY(BlueprintReadWrite) FString Title;
};

// World Event
USTRUCT(BlueprintType)
struct FWorldEvent
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite) FString EventId;
    UPROPERTY(BlueprintReadWrite) FString EventType;
    UPROPERTY(BlueprintReadWrite) FString Title;
    UPROPERTY(BlueprintReadWrite) FString Description;
    UPROPERTY(BlueprintReadWrite) FString Location;
    UPROPERTY(BlueprintReadWrite) TArray<FString> FactionsInvolved;
};

// Territory
USTRUCT(BlueprintType)
struct FTerritory
{
    GENERATED_BODY()
    
    UPROPERTY(BlueprintReadWrite) FString TerritoryId;
    UPROPERTY(BlueprintReadWrite) FString Name;
    UPROPERTY(BlueprintReadWrite) FString ControllingFaction;
    UPROPERTY(BlueprintReadWrite) float ControlStrength;
    UPROPERTY(BlueprintReadWrite) bool Contested;
};
```

---

# Integration Examples

## Complete Interaction Flow

```cpp
// 1. Player approaches NPC
void ANPCInteractionManager::OnPlayerApproachNPC(FString NpcId)
{
    // Initialize NPC
    FString Url = "https://fracturedsurvival.net/api/npc/init";
    FString Body = FString::Printf(TEXT("{\"npc_id\":\"%s\",\"player_id\":\"%s\"}"), 
        *NpcId, *PlayerId);
    SendRequest(Url, "POST", Body, [this](FString Response) {
        // NPC ready for interaction
        ShowDialogueUI();
    });
}

// 2. Player sends message
void ANPCInteractionManager::SendPlayerMessage(FString Message)
{
    FString Url = "https://fracturedsurvival.net/api/npc/action";
    FString Body = FString::Printf(
        TEXT("{\"npc_id\":\"%s\",\"player_id\":\"%s\",\"action\":\"%s\"}"),
        *CurrentNpcId, *PlayerId, *Message);
    
    SendRequest(Url, "POST", Body, [this](FString Response) {
        FNPCResponse NPCResponse = ParseResponse(Response);
        
        // Display dialogue
        DialogueWidget->SetText(NPCResponse.Dialogue);
        
        // Update animations
        UpdateNPCAnimation(NPCResponse.MoodShift, NPCResponse.Intent);
        
        // Generate voice
        GenerateVoice(CurrentNpcId, NPCResponse.Dialogue);
    });
}

// 3. Generate and play voice
void ANPCInteractionManager::GenerateVoice(FString NpcId, FString Text)
{
    FString Url = FString::Printf(
        TEXT("https://fracturedsurvival.net/api/voice/generate/%s"), *NpcId);
    FString Body = FString::Printf(TEXT("{\"text\":\"%s\"}"), *Text);
    
    SendRequest(Url, "POST", Body, [this](TArray<uint8> AudioData) {
        // Play audio
        PlayNPCVoice(AudioData);
    });
}

// 4. Check faction reputation
void ANPCInteractionManager::UpdateFactionUI()
{
    FString Url = FString::Printf(
        TEXT("https://fracturedsurvival.net/api/player/%s/factions"), *PlayerId);
    
    SendRequest(Url, "GET", "", [this](FString Response) {
        TMap<FString, FFactionReputation> Factions = ParseFactions(Response);
        FactionWidget->UpdateReputations(Factions);
    });
}

// 5. Poll for world events
void ANPCInteractionManager::CheckWorldEvents()
{
    FString Url = "https://fracturedsurvival.net/api/world/events";
    
    SendRequest(Url, "GET", "", [this](FString Response) {
        TArray<FWorldEvent> Events = ParseWorldEvents(Response);
        for (auto& Event : Events) {
            ShowWorldEventNotification(Event);
        }
    });
}
```

## Blueprint Integration Pattern

```
[Event: Player Enters NPC Trigger]
    │
    ▼
[HTTP Request: POST /api/npc/init]
    │
    ▼
[On Success: Store NPC State]
    │
    ▼
[Show Dialogue UI]
    │
    ▼
[Player Input → HTTP Request: POST /api/npc/action]
    │
    ▼
[Parse Response]
    │
    ├─▶ [Set Dialogue Text]
    │
    ├─▶ [Play Animation: MoodShift + Intent]
    │
    └─▶ [HTTP Request: POST /api/voice/generate/{npc_id}]
            │
            ▼
        [Play Audio Component]
```

---

# Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check JSON format |
| 404 | Not Found | NPC not initialized |
| 500 | Server Error | Retry or show error |
| 503 | Unavailable | Service down, retry later |

```cpp
void HandleAPIError(int32 StatusCode, FString ErrorMessage)
{
    switch (StatusCode)
    {
        case 404:
            // NPC not initialized - call /npc/init first
            InitializeNPC(CurrentNpcId);
            break;
        case 503:
            // Service unavailable - queue for retry
            QueueRetry(LastRequest);
            break;
        default:
            ShowErrorToPlayer(ErrorMessage);
    }
}
```

---

# Best Practices

1. **Always initialize NPCs** before calling `/npc/action`
2. **Cache NPC states** - don't poll every frame
3. **Use zones** for games with 50+ NPCs
4. **Poll world events** periodically (every 30-60 seconds)
5. **Handle network latency** - show loading indicators
6. **Store player_id persistently** - use Unreal's SaveGame

---

# Quick Reference

| Feature | Endpoint | Method |
|---------|----------|--------|
| Initialize NPC | `/npc/init` | POST |
| Talk to NPC | `/npc/action` | POST |
| Get NPC Status | `/npc/status/{id}` | GET |
| Generate Voice | `/voice/generate/{id}` | POST |
| Player Speech | `/speech/transcribe` | POST |
| Get Quests | `/quests/available` | GET |
| Accept Quest | `/quest/accept/{id}` | POST |
| Faction Rep | `/player/{id}/factions` | GET |
| World Events | `/world/events` | GET |
| Territory Map | `/territory/control` | GET |
| Trade Routes | `/traderoutes` | GET |

---

**API Base URL:** `https://fracturedsurvival.net/api`

**Questions?** The API is self-documenting - visit `/docs` for interactive documentation.

---

# Appendix: WAV Audio Format for Unreal Engine

## Voice Generation with WAV Format

Unreal Engine requires WAV format for audio playback. Use the `format` parameter:

### POST /voice/generate/{npc_id}

```json
// REQUEST - For Unreal Engine (WAV)
{
  "text": "Hello survivor, what brings you here?",
  "mood": "neutral",
  "format": "wav"    // ← Add this for Unreal Engine!
}

// RESPONSE
{
  "npc_id": "vera",
  "text": "Hello survivor...",
  "mood": "neutral",
  "audio_base64": "UklGRv4AAEBXQVZFZm10...",  // Base64 WAV data
  "audio_url": "data:audio/wav;base64,UklGR...",
  "format": "wav",
  "voice_info": {...}
}
```

### Format Options
| Format | Use Case | File Size |
|--------|----------|-----------|
| `mp3` | Web browsers (default) | Smaller |
| `wav` | **Unreal Engine** | Larger |

### Unreal Engine C++ Example

```cpp
void ANPCVoiceManager::GenerateVoice(FString NpcId, FString Text)
{
    FString Url = FString::Printf(
        TEXT("https://fracturedsurvival.net/api/voice/generate/%s"), *NpcId);
    
    // Request WAV format for Unreal
    FString Body = FString::Printf(
        TEXT("{\"text\":\"%s\",\"mood\":\"neutral\",\"format\":\"wav\"}"),
        *Text);
    
    SendRequest(Url, "POST", Body, [this](FString Response) {
        // Parse response
        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response);
        FJsonSerializer::Deserialize(Reader, JsonObject);
        
        // Get base64 audio
        FString AudioBase64 = JsonObject->GetStringField("audio_base64");
        
        // Decode base64 to bytes
        TArray<uint8> AudioBytes;
        FBase64::Decode(AudioBase64, AudioBytes);
        
        // Create and play sound
        PlayWavFromBytes(AudioBytes);
    });
}

void ANPCVoiceManager::PlayWavFromBytes(const TArray<uint8>& WavData)
{
    // Save to temp file
    FString TempPath = FPaths::ProjectSavedDir() / TEXT("TempVoice.wav");
    FFileHelper::SaveArrayToFile(WavData, *TempPath);
    
    // Load as sound wave
    USoundWave* SoundWave = NewObject<USoundWave>();
    // ... load from file and play
}
```

