# Fractured Survival NPC API Documentation
## For Unreal Engine Integration

**Base URL:** `https://fracturedsurvival.net/api`

---

## Table of Contents
1. [Authentication](#authentication)
2. [NPC Core Endpoints](#npc-core-endpoints)
3. [Voice Endpoints](#voice-endpoints)
4. [Player Endpoints](#player-endpoints)
5. [Quest Endpoints](#quest-endpoints)
6. [Data Models](#data-models)
7. [Example Integration Flow](#example-integration-flow)

---

## Authentication

### POST /auth/unreal-login
Authenticate a player from Unreal Engine. Creates account if doesn't exist.

**Request:**
```json
{
  "player_id": "string (required) - Unique player identifier from Unreal",
  "player_name": "string (required) - Display name"
}
```

**Response:**
```json
{
  "success": true,
  "token": "JWT_TOKEN_STRING",
  "user_id": "string",
  "player_name": "string",
  "is_new_user": true/false
}
```

**Usage:** Store the token and include in subsequent requests if needed.

---

## NPC Core Endpoints

### POST /npc/init
Initialize an NPC before interaction. Must be called first.

**Request:**
```json
{
  "npc_id": "string (required) - e.g., 'vera', 'marcus'",
  "player_id": "string (optional) - defaults to 'default_player'"
}
```

**Response:**
```json
{
  "status": "initialized" | "already_exists",
  "npc_id": "vera",
  "role": "Guarded Gatekeeper",
  "location": "Porto Cobre Gates"
}
```

---

### POST /npc/action
**Main interaction endpoint** - Send player message, get NPC response.

**Request:**
```json
{
  "npc_id": "string (required)",
  "player_id": "string (required)",
  "action": "string (required) - Player's message/action"
}
```

**Response:**
```json
{
  "npc_id": "vera",
  "player_id": "player1",
  "reflection": "Internal thoughts about the situation...",
  "dialogue": "What the NPC says to the player...",
  "inner_thoughts": "NPC's private reasoning...",
  "mood_shift": "Guarded" | "Friendly" | "Hostile" | "Curious" | etc,
  "intent": "Investigate" | "Help" | "Trade" | "Attack" | etc,
  "location": "Porto Cobre Gates",
  "emotional_state": {
    "mood": "cautious",
    "energy": 0.7,
    "stress": 0.3
  },
  "personality": {
    "friendliness": 0.4,
    "aggression": 0.3,
    "curiosity": 0.6,
    "loyalty": 0.5,
    "discipline": 0.6,
    "romanticism": 0.4,
    "opportunism": 0.5,
    "paranoia": 0.8
  }
}
```

---

### GET /npc/status/{npc_id}
Get current NPC state without interaction.

**Response:**
```json
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
  "personality": {...}
}
```

---

### GET /npc/list
Get all initialized NPCs.

**Response:**
```json
{
  "npcs": ["vera", "marcus", "finn"],
  "count": 3
}
```

---

### POST /npc/generate
Generate a random NPC with unique personality.

**Request:**
```json
{
  "name": "string (optional) - Auto-generated if not provided",
  "role": "string (optional)",
  "location": "string (optional)"
}
```

**Response:**
```json
{
  "npc_id": "generated_npc_123",
  "name": "Marcus",
  "role": "Wandering Trader",
  "personality": {...},
  "backstory": "..."
}
```

---

## Voice Endpoints

### POST /voice/assign/{npc_id}
Assign a unique voice to an NPC (auto-assigned on init, but can reassign).

**Response:**
```json
{
  "status": "assigned",
  "npc_id": "vera",
  "voice_id": "EXAVITQu4vr4xnSDxMaL",
  "voice_name": "Sarah"
}
```

---

### POST /voice/generate/{npc_id}
Generate speech audio for NPC dialogue.

**Request:**
```json
{
  "text": "string (required) - Text to convert to speech"
}
```

**Response:** 
- Content-Type: audio/mpeg
- Body: Binary audio data (MP3)

**Unreal Usage:** Save to temp file or play directly using Sound Wave.

---

### GET /voice/info/{npc_id}
Get voice information for an NPC.

**Response:**
```json
{
  "npc_id": "vera",
  "voice_id": "EXAVITQu4vr4xnSDxMaL",
  "voice_name": "Sarah",
  "gender": "female"
}
```

---

## Speech-to-Text (Player Voice Input)

### POST /speech/transcribe
Convert player voice to text.

**Request:**
```json
{
  "audio_base64": "string (required) - Base64 encoded audio",
  "language": "string (optional) - Default: 'en'"
}
```

**Supported Formats:** mp3, mp4, mpeg, mpga, m4a, wav, webm

**Response:**
```json
{
  "text": "Transcribed player speech here",
  "language": "en"
}
```

---

## Player Endpoints

### GET /player/{player_id}
Get player information and reputation.

**Response:**
```json
{
  "player_id": "player1",
  "trust_level": 0.5,
  "reputation": 0.0,
  "npc_reputations": {
    "vera": 0.3,
    "marcus": 0.7
  },
  "rumors": [],
  "remembered_topics": []
}
```

---

### GET /player/{player_id}/reputation
Get player's faction reputations.

**Response:**
```json
{
  "player_id": "player1",
  "factions": {
    "survivors": 0.5,
    "raiders": -0.3,
    "traders": 0.8
  }
}
```

---

## Quest Endpoints

### GET /quest/available/{player_id}
Get quests available to player.

**Response:**
```json
{
  "quests": [
    {
      "quest_id": "quest_001",
      "title": "Find the Medicine",
      "description": "...",
      "giver_npc": "vera",
      "reward": "supplies",
      "difficulty": "medium"
    }
  ]
}
```

---

### POST /quest/accept
Accept a quest.

**Request:**
```json
{
  "quest_id": "string (required)",
  "player_id": "string (required)"
}
```

---

### POST /quest/complete
Mark quest as complete.

**Request:**
```json
{
  "quest_id": "string (required)",
  "player_id": "string (required)"
}
```

---

## Data Models

### Emotional State
```cpp
struct FEmotionalState
{
    FString Mood;      // "neutral", "happy", "angry", "fearful", "sad"
    float Energy;      // 0.0 to 1.0
    float Stress;      // 0.0 to 1.0
};
```

### Personality Traits
```cpp
struct FPersonality
{
    float Friendliness;  // 0.0 to 1.0
    float Aggression;    // 0.0 to 1.0
    float Curiosity;     // 0.0 to 1.0
    float Loyalty;       // 0.0 to 1.0
    float Discipline;    // 0.0 to 1.0
    float Romanticism;   // 0.0 to 1.0
    float Opportunism;   // 0.0 to 1.0
    float Paranoia;      // 0.0 to 1.0
};
```

### NPC Response
```cpp
struct FNPCResponse
{
    FString NpcId;
    FString PlayerId;
    FString Dialogue;        // What NPC says (show to player)
    FString InnerThoughts;   // NPC's private thoughts (optional debug)
    FString MoodShift;       // How mood changed
    FString Intent;          // NPC's current intent
    FString Location;
    FEmotionalState EmotionalState;
    FPersonality Personality;
};
```

---

## Example Integration Flow

### Unreal Engine Pseudocode

```cpp
// 1. When player approaches NPC
void OnPlayerApproachNPC(FString NpcId, FString PlayerId)
{
    // Initialize NPC if first time
    FString Url = "https://fracturedsurvival.net/api/npc/init";
    FString Body = FString::Printf(TEXT("{\"npc_id\":\"%s\",\"player_id\":\"%s\"}"), *NpcId, *PlayerId);
    SendHttpRequest(Url, "POST", Body, &OnNPCInitialized);
}

// 2. When player sends message
void OnPlayerSendMessage(FString NpcId, FString PlayerId, FString Message)
{
    FString Url = "https://fracturedsurvival.net/api/npc/action";
    FString Body = FString::Printf(
        TEXT("{\"npc_id\":\"%s\",\"player_id\":\"%s\",\"action\":\"%s\"}"),
        *NpcId, *PlayerId, *Message
    );
    SendHttpRequest(Url, "POST", Body, &OnNPCResponse);
}

// 3. Handle NPC response
void OnNPCResponse(FString JsonResponse)
{
    // Parse JSON
    FNPCResponse Response = ParseNPCResponse(JsonResponse);
    
    // Display dialogue in UI
    ShowDialogueUI(Response.Dialogue);
    
    // Update NPC animation based on mood
    UpdateNPCAnimation(Response.MoodShift, Response.Intent);
    
    // Generate and play voice
    GenerateVoice(Response.NpcId, Response.Dialogue);
}

// 4. Generate voice audio
void GenerateVoice(FString NpcId, FString Text)
{
    FString Url = FString::Printf(
        TEXT("https://fracturedsurvival.net/api/voice/generate/%s"),
        *NpcId
    );
    FString Body = FString::Printf(TEXT("{\"text\":\"%s\"}"), *Text);
    SendHttpRequest(Url, "POST", Body, &OnVoiceGenerated);
}

// 5. Play voice audio
void OnVoiceGenerated(TArray<uint8> AudioData)
{
    // Convert to USoundWave and play
    PlayAudioFromBytes(AudioData);
}
```

---

## HTTP Response Codes

| Code | Meaning |
|------|---------|
| 200  | Success |
| 400  | Bad Request - Check your JSON |
| 404  | NPC not found - Need to initialize first |
| 500  | Server error |
| 503  | Service unavailable |

---

## Tips for Unreal Integration

1. **Always initialize NPC first** before calling /npc/action
2. **Cache NPC states** - Don't call /npc/status every frame
3. **Handle network latency** - Show loading indicator during API calls
4. **Voice audio is MP3** - May need to convert to WAV for some Unreal setups
5. **JSON parsing** - Use Unreal's FJsonObject or VaRest plugin

---

## Test Endpoints

Quick test to verify connection:
```bash
# From PowerShell/CMD on your PC:
curl https://fracturedsurvival.net/api/health

# Expected response:
{"status":"healthy","npc_embedded":true,...}
```

---

## Support

If you encounter issues, check:
1. Is the NPC initialized? (Call /npc/init first)
2. Is the JSON format correct?
3. Check HTTP response code and error message

