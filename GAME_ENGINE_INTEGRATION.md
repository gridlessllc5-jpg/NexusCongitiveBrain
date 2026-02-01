# Fractured Survival - Unreal Engine Integration Guide

## Overview

This document describes how to integrate the NPC Brain Service with Unreal Engine. The service runs as a standalone HTTP API that handles all NPC cognition, memory, and world simulation independently from the game engine.

**Architecture:**
```
Unreal Engine (C++) <--HTTP--> NPC Brain Service (Python/FastAPI)
                                      |
                                 SQLite Database
                                 (NPC memories, relationships, quests)
```

**Base URL:** `https://your-deployment-url.com/api`  
**Local Development:** `http://localhost:8001/api`

---

## Quick Start

### 1. Initialize an NPC
```cpp
// POST /api/npc/init
FString Payload = TEXT("{\"npc_id\": \"vera\", \"definition_file\": \"vera.json\"}");
// Response: {"status": "initialized", "npc_id": "vera", ...}
```

### 2. Player Interacts with NPC
```cpp
// POST /api/npc/interact/vera
FString Payload = TEXT("{\"player_id\": \"player_001\", \"action\": \"I heard there's trouble at the docks.\", \"context\": {\"location\": \"market\"}}");
// Response: {"public_response": "...", "emotional_state": {...}, "reputation_change": 0.1}
```

### 3. Advance World Time (Main Game Loop Integration)
```cpp
// POST /api/world/advance/1.0  (advance 1 hour)
// Response: {"status": "world_advanced", "events": [...], "active_npcs": [...]}
```

---

## Core API Endpoints

### World Advancement (PRIMARY ENDPOINT FOR UNREAL)

**`POST /api/world/advance/{hours}`**

This is the main endpoint Unreal Engine should call to simulate time passing. It handles:
- Memory decay (NPCs forget things over time)
- Quest expiration
- NPC goal progression
- NPC-to-NPC gossip
- Trade route execution
- World time advancement

**Request:**
```http
POST /api/world/advance/2.5
Content-Type: application/json
```

**Response:**
```json
{
  "status": "world_advanced",
  "hours_advanced": 2.5,
  "world_time": {
    "day": 3,
    "hour": 14,
    "minute": 30,
    "total_hours": 62.5
  },
  "events": [
    {"type": "memory_decay", "detail": "12 memories faded"},
    {"type": "npc_gossip", "detail": "vera gossiped with marcus"},
    {"type": "trade", "detail": "Trade on route r_001: completed"}
  ],
  "active_npcs": ["vera", "marcus", "guard_captain"]
}
```

**Recommended Usage:**
- Call every game tick or real-time interval (e.g., every 5 minutes = 1 game hour)
- Use events array to trigger in-game notifications or animations

---

### NPC Interaction

**`POST /api/npc/interact/{npc_id}`**

Have a player interact with an NPC. The NPC will:
1. Process the input through its cognitive system
2. Remember the conversation topics
3. Update reputation based on interaction
4. Return a contextually appropriate response

**Request:**
```json
{
  "player_id": "player_001",
  "action": "I need help finding my brother. He went missing near the slums.",
  "context": {
    "location": "market_square",
    "time_of_day": "evening",
    "weather": "rainy"
  }
}
```

**Response:**
```json
{
  "public_response": "Missing near the slums? That's dangerous territory. The Outcasts control that area now. I heard rumors of people disappearing... I'll keep an ear out for you.",
  "inner_thoughts": "This traveler seems desperate. The slums are no place to search alone.",
  "emotional_state": {
    "mood": "concerned",
    "energy": 0.7,
    "stress": 0.4
  },
  "topics_extracted": ["family", "location"],
  "topics_remembered": ["brother_missing", "slums_danger"],
  "reputation_change": 0.05,
  "current_reputation": 0.55,
  "heard_from_others": [
    {"source": "marcus", "topic": "slums_activity", "content": "Strange lights at night"}
  ]
}
```

---

### NPC Management

**`POST /api/npc/init`** - Initialize an NPC
```json
{
  "npc_id": "vera",
  "definition_file": "vera.json"
}
```

**`GET /api/npc/status/{npc_id}`** - Get NPC current state
```json
// Response
{
  "npc_id": "vera",
  "name": "Vera",
  "role": "Tavern Keeper",
  "location": "porto_cobre",
  "emotional_state": {"mood": "content", "energy": 0.8},
  "personality_traits": {"empathy": 0.8, "curiosity": 0.7}
}
```

**`GET /api/npc/list`** - Get all active NPCs
```json
// Response
{
  "active_npcs": [
    {"npc_id": "vera", "name": "Vera", "role": "Tavern Keeper"},
    {"npc_id": "marcus", "name": "Marcus", "role": "Blacksmith"}
  ],
  "count": 2
}
```

**`POST /api/npc/generate/random`** - Generate a random NPC
```json
{
  "role_type": "merchant",
  "name": null,
  "auto_initialize": true
}
// Response: {"npc_id": "merchant_a3f2", "role": "merchant", "personality": {...}}
```

---

### Memory System

**`GET /api/npc/memories/{npc_id}/{player_id}`** - Get what NPC remembers about player
```json
// Response
{
  "memories": [
    {
      "topic": "family",
      "content": "Has a missing brother",
      "strength": 0.85,
      "emotional_weight": 0.7
    }
  ]
}
```

**`GET /api/npc/heard-about/{npc_id}/{player_id}`** - Get secondhand info NPC heard
```json
// Response
{
  "heard_info": [
    {
      "source_npc": "marcus",
      "topic": "crimes",
      "content": "Player was seen near the warehouse fire",
      "trust_level": 0.6
    }
  ]
}
```

**`POST /api/memory/decay?hours=24`** - Manually trigger memory decay

---

### Quest System

**`POST /api/quest/generate/{npc_id}?player_id=player_001`** - Generate personalized quest
```json
// Response
{
  "quest": {
    "id": "q_vera_001",
    "title": "Find the Missing Merchant",
    "description": "Vera heard about your missing brother. She asks you to investigate similar disappearances.",
    "type": "investigation",
    "rewards": {"gold": 50, "reputation": 0.2},
    "expires_in_hours": 48
  }
}
```

**`GET /api/quests/available`** - Get all available quests
**`POST /api/quest/accept/{quest_id}`** - Accept a quest
**`POST /api/quest/complete/{quest_id}`** - Complete quest and get rewards

---

### Faction System

**`GET /api/factions`** - Get all factions and relations
```json
{
  "guards": {
    "name": "City Guards",
    "description": "Protectors of Porto Cobre",
    "relations": {
      "traders": {"score": 0.6, "type": "friendly"},
      "outcasts": {"score": -0.8, "type": "hostile"}
    }
  }
}
```

**`GET /api/territory/control`** - Get territory control map
```json
{
  "territories": {
    "market": {"controlling_faction": "traders", "control_strength": 1.0},
    "slums": {"controlling_faction": "outcasts", "control_strength": 0.8}
  }
}
```

**`POST /api/territory/{territory}/battle?attacker_faction=outcasts`** - Initiate battle
**`POST /api/battle/{battle_id}/resolve`** - Resolve battle outcome

---

### Trade Routes

**`GET /api/traderoutes`** - Get all trade routes
**`POST /api/traderoute/establish?from_npc=vera&to_npc=marcus`** - Create route
**`POST /api/traderoute/{route_id}/execute`** - Execute trade
**`POST /api/traderoute/{route_id}/disrupt?reason=attack`** - Disrupt route

---

## Unreal Engine C++ Integration Examples

### HTTP Request Helper
```cpp
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"

void UNPCBrainClient::InteractWithNPC(FString NPCId, FString PlayerId, FString Action)
{
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(FString::Printf(TEXT("%s/api/npc/interact/%s"), *BaseURL, *NPCId));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    
    TSharedPtr<FJsonObject> JsonObject = MakeShareable(new FJsonObject);
    JsonObject->SetStringField(TEXT("player_id"), PlayerId);
    JsonObject->SetStringField(TEXT("action"), Action);
    
    FString RequestBody;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestBody);
    FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
    
    Request->SetContentAsString(RequestBody);
    Request->OnProcessRequestComplete().BindUObject(this, &UNPCBrainClient::OnNPCResponseReceived);
    Request->ProcessRequest();
}

void UNPCBrainClient::OnNPCResponseReceived(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bSuccess)
{
    if (bSuccess && Response->GetResponseCode() == 200)
    {
        TSharedPtr<FJsonObject> JsonResponse;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
        
        if (FJsonSerializer::Deserialize(Reader, JsonResponse))
        {
            FString PublicResponse = JsonResponse->GetStringField(TEXT("public_response"));
            // Use PublicResponse in dialogue system
            OnNPCDialogueReceived.Broadcast(PublicResponse);
        }
    }
}
```

### World Tick Integration
```cpp
void AGameMode::AdvanceWorldTime(float DeltaHours)
{
    TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(FString::Printf(TEXT("%s/api/world/advance/%.2f"), *BaseURL, DeltaHours));
    Request->SetVerb(TEXT("POST"));
    Request->OnProcessRequestComplete().BindLambda([this](FHttpRequestPtr Req, FHttpResponsePtr Res, bool bSuccess)
    {
        if (bSuccess)
        {
            // Parse events and trigger in-game effects
            TSharedPtr<FJsonObject> JsonResponse;
            TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Res->GetContentAsString());
            FJsonSerializer::Deserialize(Reader, JsonResponse);
            
            const TArray<TSharedPtr<FJsonValue>>* Events;
            if (JsonResponse->TryGetArrayField(TEXT("events"), Events))
            {
                for (auto& Event : *Events)
                {
                    FString EventType = Event->AsObject()->GetStringField(TEXT("type"));
                    FString EventDetail = Event->AsObject()->GetStringField(TEXT("detail"));
                    // Trigger appropriate in-game effects
                    HandleWorldEvent(EventType, EventDetail);
                }
            }
        }
    });
    Request->ProcessRequest();
}
```

### Blueprint Integration
```cpp
UFUNCTION(BlueprintCallable, Category = "NPC Brain")
void TalkToNPC(FString NPCId, FString DialogueLine);

UFUNCTION(BlueprintImplementableEvent, Category = "NPC Brain")
void OnNPCReplied(const FString& Response, float ReputationChange);
```

---

## Best Practices

### 1. Connection Pooling
Keep HTTP connections alive for better performance:
```cpp
FHttpModule::Get().SetHttpTimeout(30.0f);
FHttpModule::Get().SetHttpConnectionTimeout(10.0f);
```

### 2. Async Operations
Always use async HTTP calls to avoid blocking the game thread.

### 3. Caching NPC States
Cache NPC emotional states locally and sync periodically rather than on every frame.

### 4. Batch Operations
For multiple NPC interactions, consider batching:
```cpp
// POST /api/npc/batch-interact
{
  "interactions": [
    {"npc_id": "vera", "player_id": "p1", "action": "Hello"},
    {"npc_id": "marcus", "player_id": "p1", "action": "Need weapons"}
  ]
}
```

### 5. Error Handling
```cpp
if (Response->GetResponseCode() >= 400)
{
    UE_LOG(LogNPCBrain, Error, TEXT("NPC API Error: %s"), *Response->GetContentAsString());
    // Fallback to cached response or default dialogue
}
```

---

## Performance Considerations

| Operation | Expected Latency | Recommended Frequency |
|-----------|------------------|----------------------|
| NPC Interaction | 100-500ms | On player input |
| World Advance | 50-200ms | Every 5-30 seconds |
| Get NPC Status | 10-50ms | On demand |
| Get Factions | 20-100ms | On map open |
| Battle Resolution | 100-300ms | On event |

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check request format |
| 404 | NPC Not Found | Initialize NPC first |
| 500 | Server Error | Retry with backoff |
| 503 | Service Unavailable | Server starting up |

---

## WebSocket Support (Future)

For real-time updates, WebSocket support is planned:
```
ws://your-deployment-url.com/ws/world-events
```

This will push:
- Faction war updates
- NPC gossip notifications
- Quest availability changes
- Territory control shifts

---

## Support

For issues or questions:
- Check `/api/health` for service status
- Review server logs for detailed errors
- API documentation at `/docs` (Swagger UI)
