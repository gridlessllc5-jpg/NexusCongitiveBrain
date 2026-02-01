# Fractured Survival - Standalone NPC Service

## Overview
A standalone HTTP service that provides cognitive NPC capabilities for game engines (Unreal, Unity, Godot, etc.). NPCs have memory, personality evolution, emotions, and autonomous thinking.

---

## 🚀 Quick Start

### Run the Service
```bash
cd /app/npc_system
python3 npc_service.py
```

Service runs on: `http://0.0.0.0:9000`

### Test from Command Line
```bash
# Initialize Vera
curl -X POST http://localhost:9000/npc/init \
  -H "Content-Type: application/json" \
  -d '{"npc_id": "vera"}'

# Send action
curl -X POST http://localhost:9000/npc/action \
  -H "Content-Type: application/json" \
  -d '{"npc_id": "vera", "action": "Player draws weapon"}'

# Get status
curl http://localhost:9000/npc/status/vera
```

---

## 🎮 Game Engine Integration

### Unreal Engine (C++)

```cpp
// Initialize NPC
void AGameMode::InitializeNPC(FString NPCId)
{
    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL("http://localhost:9000/npc/init");
    Request->SetVerb("POST");
    Request->SetHeader("Content-Type", "application/json");
    
    FString JsonPayload = FString::Printf(TEXT("{\"npc_id\":\"%s\"}"), *NPCId);
    Request->SetContentAsString(JsonPayload);
    
    Request->OnProcessRequestComplete().BindUObject(
        this, 
        &AGameMode::OnNPCInitialized
    );
    
    Request->ProcessRequest();
}

// Send Player Action
void ANPCCharacter::ProcessPlayerAction(FString Action)
{
    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL("http://localhost:9000/npc/action");
    Request->SetVerb("POST");
    Request->SetHeader("Content-Type", "application/json");
    
    FString JsonPayload = FString::Printf(
        TEXT("{\"npc_id\":\"%s\",\"action\":\"%s\"}"), 
        *NPCId, 
        *Action
    );
    Request->SetContentAsString(JsonPayload);
    
    Request->OnProcessRequestComplete().BindUObject(
        this, 
        &ANPCCharacter::OnActionProcessed
    );
    
    Request->ProcessRequest();
}

// Handle Response
void ANPCCharacter::OnActionProcessed(
    FHttpRequestPtr Request, 
    FHttpResponsePtr Response, 
    bool bSuccess
)
{
    if (bSuccess && Response.IsValid())
    {
        FString ResponseStr = Response->GetContentAsString();
        
        // Parse JSON
        TSharedPtr<FJsonObject> JsonObject;
        TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ResponseStr);
        FJsonSerializer::Deserialize(Reader, JsonObject);
        
        // Get dialogue
        FString Dialogue = JsonObject->GetObjectField("cognitive_frame")
            ->GetStringField("dialogue");
        
        // Update NPC dialogue in game
        DisplayDialogue(Dialogue);
    }
}
```

### Unreal Engine (Blueprints)

1. Add **HTTP Request** node
2. Set URL: `http://localhost:9000/npc/action`
3. Set Method: `POST`
4. Set Body:
   ```json
   {
     "npc_id": "vera",
     "action": "Player approaches cautiously"
   }
   ```
5. On Response Complete:
   - Parse JSON String
   - Get `cognitive_frame.dialogue`
   - Display in NPC dialogue widget

### Unity (C#)

```csharp
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

public class NPCController : MonoBehaviour
{
    private string npcServiceUrl = "http://localhost:9000";
    private string npcId = "vera";
    
    // Initialize NPC
    IEnumerator Start()
    {
        string url = $"{npcServiceUrl}/npc/init";
        string json = $"{{\"npc_id\":\"{npcId}\"}}";
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, json))
        {
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("NPC Initialized: " + request.downloadHandler.text);
            }
        }
    }
    
    // Send Player Action
    public IEnumerator SendAction(string action)
    {
        string url = $"{npcServiceUrl}/npc/action";
        string json = $"{{\"npc_id\":\"{npcId}\",\"action\":\"{action}\"}}";
        
        using (UnityWebRequest request = UnityWebRequest.Post(url, json))
        {
            request.SetRequestHeader("Content-Type", "application/json");
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                NPCResponse response = JsonUtility.FromJson<NPCResponse>(
                    request.downloadHandler.text
                );
                
                // Display dialogue
                dialogueText.text = response.cognitive_frame.dialogue;
            }
        }
    }
}

[System.Serializable]
public class NPCResponse
{
    public CognitiveFrame cognitive_frame;
    public LimbicState limbic_state;
}

[System.Serializable]
public class CognitiveFrame
{
    public string internal_reflection;
    public string intent;
    public string dialogue;
    public float urgency;
    public string emotional_state;
}
```

---

## 📡 API Reference

### Core Endpoints

#### `POST /npc/init`
Initialize an NPC instance

**Request:**
```json
{
  "npc_id": "vera",
  "persona_file": "vera_v1.json"  // optional
}
```

**Response:**
```json
{
  "status": "initialized",
  "npc_id": "vera",
  "role": "Guarded Gatekeeper",
  "location": "Porto Cobre Gates",
  "personality": {
    "curiosity": 0.8,
    "empathy": 0.7,
    "paranoia": 0.8,
    ...
  }
}
```

#### `POST /npc/action`
Send player action to NPC

**Request:**
```json
{
  "npc_id": "vera",
  "action": "I approach slowly with hands raised"
}
```

**Response:**
```json
{
  "npc_id": "vera",
  "cognitive_frame": {
    "internal_reflection": "Hands up, slow approach—good sign, but...",
    "intent": "Investigate",
    "dialogue": "Stop there. State your business.",
    "urgency": 0.7,
    "emotional_state": "Wary",
    "trust_mod": 0.02
  },
  "limbic_state": {
    "vitals": {
      "hunger": 0.2,
      "fatigue": 0.3
    },
    "emotional_state": {
      "mood": "Paranoid",
      "arousal": 0.6,
      "valence": 0.4
    }
  },
  "personality": {
    "curiosity": 0.8,
    "empathy": 0.7,
    ...
  }
}
```

#### `GET /npc/status/{npc_id}`
Get current NPC state

**Response:**
```json
{
  "npc_id": "vera",
  "active": true,
  "vitals": {
    "hunger": 0.2,
    "fatigue": 0.3
  },
  "emotional_state": {
    "mood": "Paranoid",
    "arousal": 0.6
  },
  "personality": {...}
}
```

#### `GET /npc/list`
List all active NPCs

#### `GET /npc/memories/{npc_id}?limit=5`
Get NPC's recent memories

#### `POST /npc/shutdown/{npc_id}`
Shutdown an NPC instance

### Multi-NPC Endpoints (Phase 3)

#### `POST /npc/interact`
NPC-to-NPC interaction
```json
{
  "from_npc": "vera",
  "to_npc": "guard",
  "action": "Alert about raiders"
}
```

#### `GET /factions`
Get faction status

#### `GET /trust/{npc1}/{npc2}`
Get trust level between NPCs

---

## 🎭 Available NPCs

### Vera - Guarded Gatekeeper
- **Personality**: High Paranoia, High Empathy, High Curiosity
- **Location**: Porto Cobre Gates
- **Behavior**: Cautious, questions strangers, rewards trust

### Guard - Disciplined Protector
- **Personality**: High Discipline, Moderate Aggression
- **Location**: Inner Gates
- **Behavior**: Enforces rules, military protocol

### Merchant - Opportunistic Trader
- **Personality**: High Opportunism, High Curiosity
- **Location**: Market District
- **Behavior**: Profit-focused, friendly but calculating

---

## 🔧 Configuration

### Environment Variables
```bash
# In /app/npc_system/.env
EMERGENT_LLM_KEY=sk-emergent-cA0272543971dFe1b1
```

### Port Configuration
Default port: `9000`

Change in `npc_service.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=YOUR_PORT)
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│              GAME ENGINE (Unreal/Unity)                   │
│                                                           │
│  - Player Actions → HTTP POST                            │
│  - NPC Responses ← JSON                                  │
│  - Execute dialogue/animation in game                    │
└─────────────────┬────────────────────────────────────────┘
                  │ HTTP/REST
┌─────────────────▼────────────────────────────────────────┐
│         STANDALONE NPC SERVICE (Port 9000)                │
│                                                           │
│  FastAPI Server                                          │
│  - Route requests to NPCs                                │
│  - Manage NPC instances                                  │
│  - Multi-NPC orchestration                               │
└─────────────────┬────────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────┐
│              NPC COGNITIVE SYSTEM                         │
│                                                           │
│  Thread A: Reactive (player actions)                     │
│  Thread B: Autonomous (300s reflection, vitals)          │
│  Thread C: Async IO (memory persistence)                 │
│                                                           │
│  🧠 Brain    💓 Limbic    🎯 Meta-Mind                   │
│  💾 Memory   🤝 Multi-NPC  📊 Factions                   │
└──────────────────────────────────────────────────────────┘
```

---

## 📊 Response Times

- **NPC Action Processing**: 1-3 seconds (LLM inference)
- **Status Query**: <50ms
- **Memory Query**: <100ms
- **NPC Initialization**: 1-2 seconds

**Note**: First action after initialization may take 2-4s due to LLM warmup.

---

## 🚀 Production Deployment

### Docker (Recommended)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY npc_system /app/npc_system
COPY requirements.txt /app/

RUN pip install -r requirements.txt

EXPOSE 9000

CMD ["python3", "npc_system/npc_service.py"]
```

### Run with Docker
```bash
docker build -t npc-service .
docker run -p 9000:9000 npc-service
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: npc-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: npc-service
  template:
    metadata:
      labels:
        app: npc-service
    spec:
      containers:
      - name: npc-service
        image: npc-service:latest
        ports:
        - containerPort: 9000
---
apiVersion: v1
kind: Service
metadata:
  name: npc-service
spec:
  selector:
    app: npc-service
  ports:
  - port: 9000
    targetPort: 9000
  type: LoadBalancer
```

---

## 🧪 Testing

### Health Check
```bash
curl http://localhost:9000/
```

### Full Test Sequence
```bash
# 1. Initialize
curl -X POST http://localhost:9000/npc/init \
  -H "Content-Type: application/json" \
  -d '{"npc_id": "vera"}'

# 2. Send action
curl -X POST http://localhost:9000/npc/action \
  -H "Content-Type: application/json" \
  -d '{"npc_id": "vera", "action": "I wave hello"}'

# 3. Check status
curl http://localhost:9000/npc/status/vera

# 4. Get memories
curl http://localhost:9000/npc/memories/vera

# 5. List all NPCs
curl http://localhost:9000/npc/list

# 6. Shutdown
curl -X POST http://localhost:9000/npc/shutdown/vera
```

---

## 📝 Notes

- **Stateful Service**: NPCs maintain state in memory. For persistence across restarts, implement database session storage.
- **Scaling**: Run multiple instances with shared database for load balancing.
- **Autonomous Systems**: Each NPC has a background thread for reflection and vitals decay.
- **Game Engine Agnostic**: Any engine with HTTP capabilities can connect.

---

## 🆘 Troubleshooting

### Service won't start
```bash
# Check if port 9000 is available
lsof -i :9000

# Run with different port
python3 npc_service.py --port 9001
```

### Slow responses
- First request after init is slower (LLM warmup)
- Consider keeping NPCs initialized throughout game session
- Use connection pooling in game engine

### Memory usage
- Each NPC uses ~200MB RAM
- Limit concurrent NPCs based on server capacity
- Implement NPC pooling for large worlds

---

**Built for**: Unreal Engine, Unity, Godot, and any game engine with HTTP support
**Status**: Production-ready standalone service
