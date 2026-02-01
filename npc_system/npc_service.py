"""Fractured Survival - Standalone NPC Service for Game Engines"""
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import sys
import uvicorn
import random
import sqlite3
import time
import base64
import io
import os
from pathlib import Path

# Determine base path for local vs container deployment
def get_base_path():
    if os.path.exists("/app/npc_system"):
        return Path("/app/npc_system")
    return Path(__file__).parent

BASE_PATH = get_base_path()
DATABASE_PATH = BASE_PATH / "database"
PERSONA_PATH = BASE_PATH / "persona"

# Ensure directories exist
DATABASE_PATH.mkdir(parents=True, exist_ok=True)
PERSONA_PATH.mkdir(parents=True, exist_ok=True)

# Add to Python path
sys.path.insert(0, str(BASE_PATH))

from core.npc_system import NPCSystem
from core.multi_npc import orchestrator
from core.npc_generator import npc_generator
from core.world_systems import quest_generator as world_quest_generator, trade_network, territory_system, faction_system
from core.advanced_intelligence import player_manager, relationship_graph, gossip_system, topic_memory, quest_generator, world_simulator
from core.civilization_system import npc_goal_system, quest_chain_system, trade_route_system, territorial_conflict_system
from core.scaling_system import scaling_manager
from core.voice_system import npc_voice_system, VOICE_LIBRARY
from core.auth_system import auth_system
from core.conversation_groups import conversation_manager, ConversationGroup, ResponseType

# Load environment variables
from dotenv import load_dotenv
load_dotenv(BASE_PATH / ".env")

# Re-initialize voice system with API key from env
if os.environ.get("ELEVENLABS_API_KEY"):
    from core.voice_system import NPCVoiceSystem
    npc_voice_system_instance = NPCVoiceSystem(os.environ.get("ELEVENLABS_API_KEY"))
else:
    npc_voice_system_instance = npc_voice_system

# Initialize Speech-to-Text using OpenAI-compatible adapter
# Supports both OPENAI_API_KEY and EMERGENT_LLM_KEY
try:
    from core.llm_adapter import OpenAISpeechToText
except ImportError:
    from llm_adapter import OpenAISpeechToText

stt_api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
stt_client = OpenAISpeechToText(api_key=stt_api_key)

# Background task for world simulation
simulation_task = None

# FastAPI app
app = FastAPI(
    title="Fractured Survival NPC Service",
    description="Standalone cognitive NPC system for game engines",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import WebSocket handler
from fastapi import WebSocket, WebSocketDisconnect
from core.websocket_handler import ws_manager, WebSocketHandler, event_broadcaster, MessageType

# Global instances
npc_instances: Dict[str, NPCSystem] = {}
npc_tasks: Dict[str, asyncio.Task] = {}

# WebSocket handler (initialized after dependencies are ready)
ws_handler = None

# Request Models
class InitNPCRequest(BaseModel):
    npc_id: str
    persona_file: Optional[str] = None

class ActionRequest(BaseModel):
    npc_id: str
    action: str
    player_id: Optional[str] = "default_player"  # Support multiplayer
    player_name: Optional[str] = None

class GenerateRandomNPCRequest(BaseModel):
    role_type: Optional[str] = None
    name: Optional[str] = None
    auto_initialize: bool = True

class CreateCustomNPCRequest(BaseModel):
    name: str
    role: str
    location: str
    personality: Dict[str, float]
    backstory: str
    dialogue_style: str = "Natural"
    faction: str = "citizens"
    auto_initialize: bool = True

# ============================================================================
# Authentication Models
# ============================================================================

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    player_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str  # Can be username or email
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdatePlayerNameRequest(BaseModel):
    player_name: str

class UnrealAuthRequest(BaseModel):
    """Request from Unreal Engine to create/get user"""
    unreal_player_id: str
    player_name: Optional[str] = None
    password: Optional[str] = None

class GenerateAPIKeyRequest(BaseModel):
    description: Optional[str] = None
    expires_days: Optional[int] = None

# Security scheme for JWT auth
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user from JWT token"""
    if not credentials:
        return None
    
    result = auth_system.verify_token(credentials.credentials)
    if not result.get("valid"):
        return None
    
    return result

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency that requires authentication"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = auth_system.verify_token(credentials.credentials)
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail=result.get("error", "Invalid token"))
    
    return result

# Health check
@app.get("/")
async def root():
    return {
        "service": "Fractured Survival NPC Service",
        "status": "operational",
        "active_npcs": len(npc_instances),
        "version": "1.0.0"
    }

# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/register")
async def register_user(request: RegisterRequest):
    """
    Register a new user account (web registration).
    Returns user info and JWT token on success.
    """
    result = auth_system.register(
        username=request.username,
        password=request.password,
        email=request.email,
        player_name=request.player_name,
        auth_source="web"
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/auth/login")
async def login_user(request: LoginRequest):
    """
    Login with username/email and password.
    Returns user info and JWT token on success.
    """
    result = auth_system.login(request.username, request.password)
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result

@app.get("/auth/me")
async def get_current_user_info(user: dict = Depends(require_auth)):
    """Get current authenticated user's info"""
    full_user = auth_system.get_user(user["user_id"])
    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": full_user.user_id,
        "username": full_user.username,
        "email": full_user.email,
        "player_name": full_user.player_name,
        "created_at": full_user.created_at,
        "last_login": full_user.last_login,
        "auth_source": full_user.auth_source
    }

@app.post("/auth/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify if a token is valid"""
    if not credentials:
        return {"valid": False, "error": "No token provided"}
    
    return auth_system.verify_token(credentials.credentials)

@app.put("/auth/player-name")
async def update_player_name(request: UpdatePlayerNameRequest, user: dict = Depends(require_auth)):
    """Update the player's display name"""
    success = auth_system.update_player_name(user["user_id"], request.player_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update player name")
    
    return {"success": True, "player_name": request.player_name}

@app.put("/auth/password")
async def change_password(request: ChangePasswordRequest, user: dict = Depends(require_auth)):
    """Change user's password"""
    result = auth_system.change_password(
        user["user_id"],
        request.old_password,
        request.new_password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

# ============================================================================
# Unreal Engine Authentication Endpoints
# ============================================================================

@app.post("/auth/unreal/connect")
async def unreal_connect(request: UnrealAuthRequest):
    """
    Unreal Engine player connection endpoint.
    Creates a new account if player doesn't exist, or returns existing account.
    
    Unreal Engine should:
    1. Call this endpoint when a player joins
    2. Store the returned token for subsequent API calls
    3. If is_new=True, optionally store the generated_password for future logins
    """
    result = auth_system.create_or_get_unreal_user(
        unreal_player_id=request.unreal_player_id,
        player_name=request.player_name,
        password=request.password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/auth/unreal/login")
async def unreal_login(request: UnrealAuthRequest):
    """
    Unreal Engine player login with stored credentials.
    Use this when you have the player's password stored.
    """
    if not request.password:
        raise HTTPException(status_code=400, detail="Password required for login")
    
    result = auth_system.validate_unreal_credentials(
        request.unreal_player_id,
        request.password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result

# ============================================================================
# API Key Management (for server-to-server auth)
# ============================================================================

@app.post("/auth/api-key")
async def create_api_key(request: GenerateAPIKeyRequest, user: dict = Depends(require_auth)):
    """
    Generate an API key for server-to-server authentication.
    Useful for Unreal Engine dedicated servers.
    """
    result = auth_system.generate_api_key(
        user["user_id"],
        request.description,
        request.expires_days
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.get("/auth/api-key/validate")
async def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Validate an API key and return associated user info"""
    result = auth_system.validate_api_key(x_api_key)
    
    if not result["valid"]:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result

@app.delete("/auth/api-key/{key_id}")
async def revoke_api_key(key_id: str, user: dict = Depends(require_auth)):
    """Revoke an API key"""
    success = auth_system.revoke_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"success": True, "message": "API key revoked"}

@app.get("/auth/users")
async def list_users(limit: int = 100, offset: int = 0, user: dict = Depends(require_auth)):
    """List all users (admin endpoint)"""
    return auth_system.list_users(limit, offset)

# Initialize NPC
@app.post("/npc/init")
async def initialize_npc(request: InitNPCRequest):
    try:
        npc_id = request.npc_id
        if npc_id in npc_instances:
            return {"status": "already_exists", "npc_id": npc_id}
        
        if request.persona_file:
            persona_path = str(PERSONA_PATH / request.persona_file)
        else:
            persona_map = {
                "vera": "vera_v1.json",
                "guard": "guard_v1.json",
                "merchant": "merchant_v1.json"
            }
            persona_file = persona_map.get(npc_id.lower(), "vera_v1.json")
            persona_path = str(PERSONA_PATH / persona_file)
        
        npc = NPCSystem(persona_path)
        npc_instances[npc_id] = npc
        
        faction_map = {"vera": "guards", "guard": "guards", "merchant": "traders"}
        faction = faction_map.get(npc_id.lower(), "citizens")
        orchestrator.register_npc(npc_id, npc, faction)
        
        # Register with world simulator
        world_simulator.register_npc(npc_id)
        
        task = asyncio.create_task(npc.start_autonomous_systems())
        npc_tasks[npc_id] = task
        
        # Auto-assign voice based on persona gender
        try:
            persona = npc.persona if hasattr(npc, 'persona') else {}
            if isinstance(persona, dict):
                gender = persona.get('gender', 'male')
                role = persona.get('role', 'citizen')
                personality = persona.get('personality', {})
            else:
                gender = getattr(persona, 'gender', 'male')
                role = getattr(persona, 'role', 'citizen')
                personality = getattr(persona, 'personality', {})
            
            if hasattr(personality, '__dict__'):
                personality = vars(personality)
            
            # Assign unique voice with correct gender
            npc_voice_system_instance.assign_unique_voice(
                npc_id=npc_id,
                role=role,
                gender=gender,
                faction=faction,
                personality=personality if isinstance(personality, dict) else {}
            )
        except Exception as voice_err:
            print(f"Voice assignment warning for {npc_id}: {voice_err}")
        
        return {
            "status": "initialized",
            "npc_id": npc_id,
            "role": npc.persona["role"],
            "location": npc.persona["location"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Process action with player tracking (supports multiplayer)
@app.post("/npc/action")
async def process_action(request: ActionRequest):
    try:
        npc_id = request.npc_id
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail="NPC not found")
        
        # Get or create player session
        player = player_manager.get_or_create_player(request.player_id, request.player_name)
        
        # Get player's reputation with this NPC
        reputation = player_manager.get_player_reputation(player.player_id, npc_id)
        
        # Get rumors about this player that NPC has heard
        rumors = gossip_system.get_rumors_about_player(player.player_id, npc_id)
        
        # Extract and store topics from player message
        extracted_topics = topic_memory.extract_topics(player.player_id, npc_id, request.action)
        
        # Get relevant past topics for context (direct memories)
        relevant_topics = topic_memory.get_relevant_topics(player.player_id, npc_id, request.action)
        topic_context = topic_memory.format_topics_for_context(relevant_topics)
        
        # Get shared memories (what other NPCs told this NPC about the player)
        shared_memories = topic_memory.get_shared_memories_about_player(npc_id, player.player_id)
        shared_context = topic_memory.format_shared_memories_for_context(shared_memories)
        
        # Build enriched context for NPC
        context = f"Player {player.player_name} (reputation with you: {reputation:.2f})"
        if rumors:
            context += f". You've heard: {rumors[0]['content']}"
        if topic_context:
            context += f"\n\n{topic_context}"
        if shared_context:
            context += f"\n{shared_context}"
        
        enriched_action = f"{context}\n\nPlayer's current action: {request.action}"
        
        # Process through NPC
        npc = npc_instances[npc_id]
        response = await npc.process_player_action(enriched_action)
        
        # Determine reputation change based on NPC response
        cognitive_frame = response["cognitive_frame"]
        rep_change = cognitive_frame.get("trust_mod", 0.0)
        
        # Update reputation
        if rep_change != 0:
            player_manager.update_reputation(player.player_id, npc_id, rep_change)
        
        # Log action
        player_manager.log_action(
            player.player_id, npc_id, request.action,
            cognitive_frame.get("dialogue", ""),
            rep_change
        )
        
        # Create rumor (30% chance)
        if random.random() < 0.3:
            outcome = "positive" if rep_change > 0 else "negative" if rep_change < 0 else "neutral"
            rumor = gossip_system.create_rumor(player.player_id, npc_id, request.action, outcome)
            
            # Spread to nearby NPCs (NPCs in same faction)
            for other_npc_id in npc_instances.keys():
                if other_npc_id != npc_id and random.random() < 0.5:
                    gossip_system.spread_rumor(npc_id, other_npc_id, rumor.rumor_id)
        
        # Mark referenced topics
        for topic in relevant_topics[:2]:  # Mark top 2 as referenced
            topic_memory.mark_topic_referenced(topic["topic_id"])
        
        # Auto-share memories with other NPCs (gossip happens naturally)
        memories_shared = 0
        if len(extracted_topics) > 0 and random.random() < 0.4:  # 40% chance to gossip about new info
            for other_npc_id in npc_instances.keys():
                if other_npc_id != npc_id:
                    memories_shared += topic_memory.auto_share_memories(npc_id, other_npc_id, player.player_id)
        
        return {
            "npc_id": npc_id,
            "player_id": player.player_id,
            "reputation": player_manager.get_player_reputation(player.player_id, npc_id),
            "topics_extracted": len(extracted_topics),
            "topics_remembered": len(relevant_topics),
            "heard_from_others": len(shared_memories),
            "memories_shared": memories_shared,
            "cognitive_frame": response["cognitive_frame"],
            "limbic_state": response["limbic_state"],
            "personality": response["personality_snapshot"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get player info
@app.get("/player/{player_id}")
async def get_player_info(player_id: str):
    try:
        player = player_manager.get_or_create_player(player_id)
        
        # Get all reputations
        conn = sqlite3.connect(str(DATABASE_PATH / "memory_vault.db"))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT npc_id, reputation FROM player_npc_reputation WHERE player_id = ?",
            (player_id,)
        )
        reputations = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        # Get rumors about player
        rumors = gossip_system.get_rumors_about_player(player_id)
        
        # Get remembered topics
        topics = topic_memory.get_all_topics_for_player(player_id)
        
        return {
            "player_id": player.player_id,
            "player_name": player.player_name,
            "total_interactions": player.total_interactions,
            "global_reputation": player.global_reputation,
            "npc_reputations": reputations,
            "rumors": rumors[:5],  # Top 5 rumors
            "remembered_topics": topics[:10]  # Top 10 topics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get topics NPC remembers about player
@app.get("/npc/memories/{npc_id}/{player_id}")
async def get_npc_memories_about_player(npc_id: str, player_id: str):
    try:
        topics = topic_memory.get_all_topics_for_player(player_id, npc_id)
        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "memories": topics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get NPC relationships
@app.get("/npc/relationships/{npc_id}")
async def get_npc_relationships(npc_id: str):
    try:
        relationships = relationship_graph.get_npc_social_circle(npc_id)
        return {"npc_id": npc_id, "relationships": relationships}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simulate NPC gossip
@app.post("/npc/gossip/{from_npc}/{to_npc}")
async def simulate_gossip(from_npc: str, to_npc: str):
    try:
        # Get rumors from_npc knows
        conn = sqlite3.connect(str(DATABASE_PATH / "memory_vault.db"))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT rumor_id FROM npc_heard_rumors WHERE npc_id = ? ORDER BY heard_at DESC LIMIT 3",
            (from_npc,)
        )
        rumor_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        spread_count = 0
        for rumor_id in rumor_ids:
            if random.random() < 0.7:  # 70% chance to share each rumor
                gossip_system.spread_rumor(from_npc, to_npc, rumor_id)
                spread_count += 1
        
        # Update relationship (gossip brings NPCs closer)
        relationship_graph.update_relationship(from_npc, to_npc, 0.05)
        
        return {
            "from": from_npc,
            "to": to_npc,
            "rumors_shared": spread_count,
            "relationship_improved": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Share memories between NPCs (deep gossip about specific players)
@app.post("/npc/share-memories/{from_npc}/{to_npc}")
async def share_memories_between_npcs(from_npc: str, to_npc: str, player_id: str = None):
    """NPCs share what they know about players with each other"""
    try:
        memories_shared = topic_memory.auto_share_memories(from_npc, to_npc, player_id)
        
        # Update relationship
        if memories_shared > 0:
            relationship_graph.update_relationship(from_npc, to_npc, 0.03 * memories_shared)
        
        return {
            "from": from_npc,
            "to": to_npc,
            "player_id": player_id,
            "memories_shared": memories_shared
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get what an NPC has heard about a player from others
@app.get("/npc/heard-about/{npc_id}/{player_id}")
async def get_heard_about_player(npc_id: str, player_id: str):
    """Get secondhand information NPC has heard about a player"""
    try:
        shared = topic_memory.get_shared_memories_about_player(npc_id, player_id)
        direct = topic_memory.get_all_topics_for_player(player_id, npc_id)
        
        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "direct_memories": direct,
            "heard_from_others": shared
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all players
@app.get("/players")
async def list_players():
    try:
        conn = sqlite3.connect(str(DATABASE_PATH / "memory_vault.db"))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT player_id, player_name, total_interactions, global_reputation FROM player_sessions"
        )
        players = [
            {
                "player_id": row[0],
                "player_name": row[1],
                "total_interactions": row[2],
                "global_reputation": row[3]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return {"players": players}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get status
@app.get("/npc/status/{npc_id}")
async def get_status(npc_id: str):
    try:
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail="NPC not found")
        
        npc = npc_instances[npc_id]
        limbic_state = npc.limbic.get_state_summary()
        
        return {
            "npc_id": npc_id,
            "active": True,
            "vitals": limbic_state["vitals"],
            "emotional_state": limbic_state["emotional_state"],
            "personality": npc.personality
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List NPCs
@app.get("/npc/list")
async def list_npcs():
    return {
        "npcs": [
            {
                "npc_id": npc_id,
                "role": npc.persona["role"],
                "location": npc.persona["location"],
                "mood": npc.limbic.emotional_state.mood
            }
            for npc_id, npc in npc_instances.items()
        ]
    }

# ============================================================================
# Memory Decay System Endpoints
# ============================================================================

@app.post("/memory/decay")
async def apply_memory_decay(hours: float = 24.0):
    """Apply memory decay to all memories (simulate time passing)"""
    try:
        result = topic_memory.apply_memory_decay(hours)
        return {
            "status": "decay_applied",
            "hours_simulated": hours,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/cleanup")
async def cleanup_forgotten_memories(threshold: float = 0.1):
    """Remove memories that have decayed below threshold"""
    try:
        result = topic_memory.cleanup_forgotten_memories(threshold)
        return {
            "status": "cleanup_complete",
            "threshold": threshold,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/status")
async def get_memory_status(player_id: str = None, npc_id: str = None):
    """Get memory decay status for debugging"""
    try:
        result = topic_memory.get_memory_status(player_id, npc_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/reinforce/{player_id}/{npc_id}")
async def reinforce_memories(player_id: str, npc_id: str, keywords: List[str] = None):
    """Manually reinforce memories matching keywords"""
    try:
        if not keywords:
            keywords = []
        reinforced = topic_memory.reinforce_memory(player_id, npc_id, keywords)
        return {
            "status": "reinforced",
            "memories_reinforced": reinforced
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Dynamic Quest Generation Endpoints
# ============================================================================

@app.post("/quest/generate/{npc_id}")
async def generate_quest(npc_id: str, player_id: str = None):
    """Generate a quest from NPC based on memories about player"""
    try:
        quest = quest_generator.generate_quest_from_memories(npc_id, player_id)
        return {
            "status": "quest_generated",
            "quest": {
                "quest_id": quest.quest_id,
                "npc_id": quest.npc_id,
                "title": quest.title,
                "description": quest.description,
                "quest_type": quest.quest_type,
                "objectives": quest.objectives,
                "rewards": quest.rewards,
                "difficulty": quest.difficulty,
                "expires_at": quest.expires_at,
                "personalized_for": player_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quests/available")
async def get_available_quests(npc_id: str = None, player_id: str = None):
    """Get all available quests, optionally filtered"""
    try:
        quests = quest_generator.get_available_quests(npc_id, player_id)
        return {"quests": quests, "total": len(quests)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quest/accept/{quest_id}")
async def accept_quest(quest_id: str, player_id: str):
    """Player accepts a quest"""
    try:
        success = quest_generator.accept_quest(quest_id, player_id)
        if success:
            return {"status": "accepted", "quest_id": quest_id}
        else:
            raise HTTPException(status_code=400, detail="Quest not available or already taken")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quest/complete/{quest_id}")
async def complete_quest(quest_id: str):
    """Mark quest as completed and get rewards"""
    try:
        result = quest_generator.complete_quest(quest_id)
        if result["success"]:
            return {"status": "completed", **result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to complete quest"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quests/expire")
async def expire_old_quests():
    """Clean up expired quests"""
    try:
        expired = quest_generator.expire_old_quests()
        return {"status": "cleanup_complete", "quests_expired": expired}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# World Simulation Endpoints - Living, Breathing World
# ============================================================================

async def simulation_loop():
    """Background task that runs the world simulation"""
    global simulation_task
    while world_simulator.is_running:
        try:
            result = await world_simulator.tick()
            # Log significant events
            if result.get("events"):
                for event in result["events"]:
                    print(f"[World] {event['type']}: {event['detail']}")
        except Exception as e:
            print(f"[World] Simulation error: {e}")
        
        await asyncio.sleep(world_simulator.tick_interval)

@app.post("/world/start")
async def start_world_simulation(time_scale: float = 1.0, tick_interval: int = 60):
    """Start the world simulation"""
    global simulation_task
    
    if world_simulator.is_running:
        return {"status": "already_running", **world_simulator.get_status()}
    
    # Configure simulation
    world_simulator.configure(time_scale, tick_interval)
    world_simulator.is_running = True
    
    # Register all active NPCs
    for npc_id in npc_instances.keys():
        world_simulator.register_npc(npc_id)
    
    # Start background task
    simulation_task = asyncio.create_task(simulation_loop())
    
    return {
        "status": "started",
        "message": f"World simulation started at {time_scale}x speed",
        **world_simulator.get_status()
    }

@app.post("/world/stop")
async def stop_world_simulation():
    """Stop the world simulation"""
    global simulation_task
    
    if not world_simulator.is_running:
        return {"status": "not_running"}
    
    world_simulator.is_running = False
    
    if simulation_task:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
        simulation_task = None
    
    return {
        "status": "stopped",
        "final_stats": world_simulator.stats,
        "world_time": world_simulator.get_world_time()
    }

@app.get("/world/status")
async def get_world_status():
    """Get current world simulation status"""
    return world_simulator.get_status()

@app.post("/world/tick")
async def manual_world_tick():
    """Manually trigger one world simulation tick"""
    try:
        result = await world_simulator.tick()
        return {
            "status": "tick_complete",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/world/configure")
async def configure_world(time_scale: float = None, tick_interval: int = None):
    """Configure world simulation parameters"""
    config = world_simulator.configure(time_scale, tick_interval)
    return {
        "status": "configured",
        **config
    }

@app.get("/world/events")
async def get_world_events(limit: int = 20):
    """Get recent world events"""
    events = world_simulator.event_log[-limit:]
    return {
        "events": events,
        "total": len(events),
        "world_time": world_simulator.get_world_time()
    }

# ============================================================================
# Faction System Endpoints
# ============================================================================

@app.get("/factions")
async def get_all_factions():
    """Get all factions and their status"""
    return faction_system.get_all_factions_status()

@app.get("/faction/events")
async def get_faction_events(limit: int = 10):
    """Get recent faction events"""
    return {"events": faction_system.get_recent_events(limit)}

@app.get("/faction/relation/{faction1}/{faction2}")
async def get_faction_relation(faction1: str, faction2: str):
    """Get relationship between two factions"""
    relation = faction_system.get_relation(faction1, faction2)
    return {
        "faction1": relation.faction1,
        "faction2": relation.faction2,
        "score": relation.relation_score,
        "type": relation.relation_type,
        "recent_history": relation.history[-5:]
    }

@app.get("/faction/{faction_id}")
async def get_faction_details(faction_id: str):
    """Get detailed info about a specific faction"""
    status = faction_system.get_faction_status(faction_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status

@app.post("/faction/event")
async def trigger_faction_event(event_type: str = "skirmish", faction1: str = None, faction2: str = None, description: str = "Faction event"):
    """Trigger a faction event (skirmish, trade_deal, betrayal, alliance_formed)"""
    if not faction1 or not faction2:
        raise HTTPException(status_code=400, detail="Need faction1 and faction2 parameters")
    
    factions = [faction1, faction2]
    event = faction_system.trigger_faction_event(event_type, factions, description)
    return {"status": "event_triggered", "event": event}

@app.get("/player/{player_id}/factions")
async def get_player_faction_reputation(player_id: str):
    """Get player's reputation with all factions"""
    reps = faction_system.get_player_faction_reputation(player_id)
    return {
        "player_id": player_id,
        "faction_reputations": reps
    }

@app.post("/player/{player_id}/faction/{faction_id}")
async def update_player_faction_rep(player_id: str, faction_id: str, change: float):
    """Update player's reputation with a faction"""
    new_rep = faction_system.update_player_faction_reputation(player_id, faction_id, change)
    return {
        "player_id": player_id,
        "faction": faction_id,
        "new_reputation": new_rep,
        "ripple_effects_applied": True
    }

# ============================================================================
# Phase 4: Dynamic Civilizations API
# ============================================================================

# --- NPC Goals ---
@app.post("/npc/{npc_id}/goal/generate")
async def generate_npc_goal(npc_id: str, faction: str = "citizens"):
    """Generate an autonomous goal for an NPC"""
    goal = npc_goal_system.generate_goal(npc_id, faction)
    return {
        "status": "goal_generated",
        "goal": {
            "goal_id": goal.goal_id,
            "type": goal.goal_type,
            "description": goal.description,
            "target": goal.target,
            "priority": goal.priority,
            "steps": goal.steps
        }
    }

@app.get("/npc/{npc_id}/goals")
async def get_npc_goals(npc_id: str, status: str = None):
    """Get all goals for an NPC"""
    goals = npc_goal_system.get_npc_goals(npc_id, status)
    return {"npc_id": npc_id, "goals": goals}

@app.post("/goal/{goal_id}/progress")
async def update_goal_progress(goal_id: str, delta: float = 0.1):
    """Update progress on a goal"""
    result = npc_goal_system.update_goal_progress(goal_id, delta)
    return result

@app.post("/goal/{goal_id}/abandon")
async def abandon_goal(goal_id: str):
    """Abandon a goal"""
    success = npc_goal_system.abandon_goal(goal_id)
    return {"success": success, "goal_id": goal_id}

# --- Quest Chains ---
@app.post("/questchain/create/{npc_id}")
async def create_quest_chain(npc_id: str, faction: str = "citizens", player_id: str = None):
    """Create a new quest chain"""
    chain = quest_chain_system.create_chain(npc_id, faction, player_id)
    return {
        "status": "chain_created",
        "chain": {
            "chain_id": chain.chain_id,
            "name": chain.name,
            "description": chain.description,
            "quests": chain.quests,
            "rewards": chain.rewards_on_completion
        }
    }

@app.get("/questchains")
async def get_quest_chains(player_id: str = None):
    """Get available quest chains"""
    chains = quest_chain_system.get_available_chains(player_id)
    return {"chains": chains, "total": len(chains)}

@app.post("/questchain/{chain_id}/start")
async def start_quest_chain(chain_id: str, player_id: str):
    """Start a quest chain"""
    result = quest_chain_system.start_chain(chain_id, player_id)
    return result

@app.post("/questchain/{chain_id}/advance")
async def advance_quest_chain(chain_id: str):
    """Advance to next quest in chain"""
    result = quest_chain_system.advance_chain(chain_id)
    return result

# --- Trade Routes ---
@app.post("/traderoute/establish")
async def establish_trade_route(from_npc: str, to_npc: str, from_loc: str = None, to_loc: str = None):
    """Establish a new trade route"""
    route = trade_route_system.establish_route(from_npc, to_npc, from_loc, to_loc)
    return {
        "status": "route_established",
        "route": {
            "route_id": route.route_id,
            "from": f"{route.from_npc} @ {route.from_location}",
            "to": f"{route.to_npc} @ {route.to_location}",
            "goods": route.goods,
            "profit_margin": route.profit_margin,
            "risk_level": route.risk_level
        }
    }

@app.get("/traderoutes")
async def get_trade_routes(status: str = None):
    """Get all trade routes"""
    routes = trade_route_system.get_all_routes(status)
    return {"routes": routes, "total": len(routes)}

@app.post("/traderoute/{route_id}/execute")
async def execute_trade(route_id: str):
    """Execute a trade on a route"""
    result = trade_route_system.execute_trade(route_id)
    return result

@app.post("/traderoute/{route_id}/disrupt")
async def disrupt_trade_route(route_id: str, reason: str = "attack"):
    """Disrupt a trade route"""
    success = trade_route_system.disrupt_route(route_id, reason)
    return {"success": success, "route_id": route_id, "new_status": "disrupted"}

@app.post("/traderoute/{route_id}/restore")
async def restore_trade_route(route_id: str):
    """Restore a disrupted trade route"""
    success = trade_route_system.restore_route(route_id)
    return {"success": success, "route_id": route_id, "new_status": "active"}

# --- Territorial Conflicts ---
@app.get("/territory/control")
async def get_territory_control():
    """Get current territory control status"""
    control = territorial_conflict_system.get_territory_control()
    return {"territories": control}

@app.post("/territory/{territory}/battle")
async def initiate_territorial_battle(territory: str, attacker_faction: str):
    """Initiate a battle for territory"""
    battle = territorial_conflict_system.initiate_battle(territory, attacker_faction)
    if not battle:
        raise HTTPException(status_code=400, detail="Cannot attack own territory or invalid territory")
    return {
        "status": "battle_initiated",
        "battle": {
            "battle_id": battle.battle_id,
            "territory": battle.territory,
            "attacker": battle.attacker_faction,
            "defender": battle.defender_faction,
            "attacker_strength": battle.attacker_strength,
            "defender_strength": battle.defender_strength
        }
    }

@app.post("/battle/{battle_id}/resolve")
async def resolve_battle(battle_id: str):
    """Resolve a territorial battle"""
    result = territorial_conflict_system.resolve_battle(battle_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/battles")
async def get_battle_history(territory: str = None, limit: int = 10):
    """Get battle history"""
    battles = territorial_conflict_system.get_battle_history(territory, limit)
    return {"battles": battles, "total": len(battles)}

# --- World Advancement (for Unreal Engine) ---
@app.post("/world/advance/{hours}")
async def advance_world_state(hours: float):
    """
    Advance the world state by specified hours.
    This is the main API for Unreal Engine to call to simulate time passing.
    Returns a summary of what happened during the time period.
    """
    events = []
    
    # 1. Apply memory decay
    decay_result = topic_memory.apply_memory_decay(hours)
    if decay_result.get("direct_memories_decayed", 0) > 0:
        events.append({
            "type": "memory_decay",
            "detail": f"{decay_result['direct_memories_decayed']} memories faded"
        })
    
    # 2. Cleanup forgotten memories
    cleanup = topic_memory.cleanup_forgotten_memories(0.1)
    if cleanup.get("direct_forgotten", 0) > 0:
        events.append({
            "type": "memories_forgotten",
            "detail": f"{cleanup['direct_forgotten']} memories completely forgotten"
        })
    
    # 3. Expire quests
    expired = quest_generator.expire_old_quests()
    if expired > 0:
        events.append({
            "type": "quests_expired",
            "detail": f"{expired} quests expired"
        })
    
    # 4. Process NPC goals (advance random goals)
    active_npcs = list(npc_instances.keys())
    goals_progressed = 0
    for npc_id in active_npcs:
        goals = npc_goal_system.get_npc_goals(npc_id, "active")
        for goal in goals[:1]:  # Progress first goal
            if random.random() < 0.3:  # 30% chance per hour
                npc_goal_system.update_goal_progress(goal["goal_id"], 0.1 * hours)
                goals_progressed += 1
    
    if goals_progressed > 0:
        events.append({
            "type": "goals_progressed",
            "detail": f"{goals_progressed} NPC goals made progress"
        })
    
    # 5. Random NPC gossip
    if len(active_npcs) >= 2 and random.random() < min(0.5, hours * 0.1):
        npc1, npc2 = random.sample(active_npcs, 2)
        gossip_system.spread_all_rumors(npc1, npc2)
        topic_memory.auto_share_memories(npc1, npc2)
        events.append({
            "type": "npc_gossip",
            "detail": f"{npc1} gossiped with {npc2}"
        })
    
    # 6. Random trade execution
    routes = trade_route_system.get_all_routes("active")
    if routes and random.random() < min(0.4, hours * 0.05):
        route = random.choice(routes)
        result = trade_route_system.execute_trade(route["route_id"])
        events.append({
            "type": "trade",
            "detail": f"Trade on route {route['route_id']}: {result.get('message', 'completed')}"
        })
    
    # Update world time
    world_simulator.advance_time(hours * 3600)
    
    return {
        "status": "world_advanced",
        "hours_advanced": hours,
        "world_time": world_simulator.get_world_time(),
        "events": events,
        "active_npcs": active_npcs
    }

# Generate random NPC
@app.post("/npc/generate/random")
async def generate_random_npc(request: GenerateRandomNPCRequest):
    try:
        npc_def = npc_generator.generate_random_npc(
            role_type=request.role_type,
            name=request.name
        )
        
        npc_id = npc_def["npc_id"]
        filename = npc_generator.save_npc_to_file(npc_id)
        
        if request.auto_initialize:
            npc = NPCSystem(filename)
            npc_instances[npc_id] = npc
            faction = npc_def.get("faction", "citizens")
            orchestrator.register_npc(npc_id, npc, faction)
            task = asyncio.create_task(npc.start_autonomous_systems())
            npc_tasks[npc_id] = task
        
        return {
            "status": "generated",
            "npc_id": npc_id,
            "role": npc_def["role"],
            "personality": npc_def["personality"],
            "initialized": request.auto_initialize
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create custom NPC
@app.post("/npc/create/custom")
async def create_custom_npc(request: CreateCustomNPCRequest):
    try:
        npc_def = npc_generator.create_custom_npc(
            name=request.name,
            role=request.role,
            location=request.location,
            personality=request.personality,
            backstory=request.backstory,
            dialogue_style=request.dialogue_style,
            faction=request.faction
        )
        
        npc_id = npc_def["npc_id"]
        filename = npc_generator.save_npc_to_file(npc_id)
        
        if request.auto_initialize:
            npc = NPCSystem(filename)
            npc_instances[npc_id] = npc
            orchestrator.register_npc(npc_id, npc, request.faction)
            task = asyncio.create_task(npc.start_autonomous_systems())
            npc_tasks[npc_id] = task
        
        return {
            "status": "created",
            "npc_id": npc_id,
            "role": npc_def["role"],
            "initialized": request.auto_initialize
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get templates
@app.get("/npc/templates")
async def get_npc_templates():
    from core.npc_generator import ROLE_TEMPLATES
    templates = {}
    for role_type, template in ROLE_TEMPLATES.items():
        templates[role_type] = {
            "roles": template["roles"],
            "locations": template["locations"]
        }
    return {"templates": templates}

# Generate quest
@app.post("/quest/generate/{npc_id}")
async def generate_quest_for_npc(npc_id: str):
    try:
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail="NPC not found")
        
        npc = npc_instances[npc_id]
        limbic_state = npc.limbic.get_state_summary()
        
        quest = quest_generator.generate_quest_from_npc(
            npc_id=npc_id,
            npc_personality=npc.personality,
            npc_vitals=limbic_state["vitals"],
            npc_goal=npc.persona.get("current_goal", "survive")
        )
        
        return {
            "quest_id": quest.quest_id,
            "title": quest.title,
            "description": quest.description,
            "quest_type": quest.quest_type,
            "difficulty": quest.difficulty
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get quests
@app.get("/quests/available")
async def get_available_quests():
    quests = quest_generator.get_available_quests()
    return {
        "quests": [{
            "quest_id": q.quest_id,
            "title": q.title,
            "quest_type": q.quest_type,
            "difficulty": q.difficulty
        } for q in quests]
    }

# Territory overview
@app.get("/territory/overview")
async def get_territorial_overview():
    return territory_system.get_territorial_overview()

# ============================================================================
# Phase 5: Scaling & Performance Endpoints
# ============================================================================

# --- Batch Endpoints ---

class BatchInteractionRequest(BaseModel):
    """Request for batch NPC interactions"""
    interactions: List[Dict]  # [{npc_id, player_id, action}, ...]

@app.post("/batch/interact")
async def batch_interact(request: BatchInteractionRequest):
    """
    Process multiple NPC interactions in a single request.
    Optimized for game engines that need to update multiple NPCs.
    """
    start_time = time.time()
    results = []
    errors = []
    
    for interaction in request.interactions:
        npc_id = interaction.get("npc_id")
        player_id = interaction.get("player_id", "default_player")
        action = interaction.get("action", "")
        
        try:
            if npc_id not in npc_instances:
                errors.append({"npc_id": npc_id, "error": "NPC not initialized"})
                continue
            
            npc = npc_instances[npc_id]
            
            # Record interaction for tiered updates
            scaling_manager.record_interaction(npc_id)
            
            # Process action
            player = player_manager.get_or_create_player(player_id)
            response = await npc.process_player_action(action)
            
            results.append({
                "npc_id": npc_id,
                "response": response.get("cognitive_frame", {}).get("dialogue", ""),
                "mood": response.get("cognitive_frame", {}).get("emotional_state", "neutral")
            })
            
        except Exception as e:
            errors.append({"npc_id": npc_id, "error": str(e)})
    
    processing_time = time.time() - start_time
    scaling_manager.performance.record("batch_interact", processing_time)
    
    return {
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors if errors else None,
        "processing_time_ms": round(processing_time * 1000, 2)
    }

class BatchNPCInitRequest(BaseModel):
    """Request for batch NPC initialization"""
    npc_ids: List[str]

@app.post("/batch/init")
async def batch_init_npcs(request: BatchNPCInitRequest):
    """Initialize multiple NPCs in a single request"""
    start_time = time.time()
    initialized = []
    errors = []
    
    # Map NPC IDs to persona files (same logic as regular init)
    persona_map = {
        "vera": "vera_v1.json",
        "guard": "guard_v1.json",
        "merchant": "merchant_v1.json"
    }
    
    for npc_id in request.npc_ids:
        try:
            if npc_id in npc_instances:
                initialized.append({"npc_id": npc_id, "status": "already_exists"})
                continue
            
            # Use persona map or default to vera
            persona_file_name = persona_map.get(npc_id.lower(), "vera_v1.json")
            persona_file = str(PERSONA_PATH / persona_file_name)
            npc = NPCSystem(persona_file)
            npc_instances[npc_id] = npc
            
            # Register with scaling system
            scaling_manager.register_npc(npc_id)
            
            # Register with orchestrator
            faction_map = {"vera": "guards", "guard": "guards", "merchant": "traders"}
            faction = faction_map.get(npc_id.lower(), "citizens")
            orchestrator.register_npc(npc_id, npc, faction)
            
            # Start autonomous systems
            task = asyncio.create_task(npc.start_autonomous_systems())
            npc_tasks[npc_id] = task
            
            initialized.append({
                "npc_id": npc_id,
                "status": "initialized",
                "name": npc.persona.get("name", npc_id) if isinstance(npc.persona, dict) else npc_id
            })
            
        except Exception as e:
            errors.append({"npc_id": npc_id, "error": str(e)})
    
    processing_time = time.time() - start_time
    
    return {
        "initialized": len(initialized),
        "errors": len(errors),
        "results": initialized,
        "error_details": errors if errors else None,
        "processing_time_ms": round(processing_time * 1000, 2)
    }

# --- Paginated List Endpoints ---

@app.get("/npc/list/paginated")
async def get_npcs_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tier: str = Query(None, description="Filter by tier: active, nearby, idle, dormant")
):
    """Get paginated list of NPCs with optional tier filtering"""
    all_npcs = list(npc_instances.keys())
    
    # Filter by tier if specified
    if tier:
        tier_npcs = []
        for npc_id in all_npcs:
            state = scaling_manager.tiered_updates._npc_states.get(npc_id)
            if state and state.tier == tier:
                tier_npcs.append(npc_id)
        all_npcs = tier_npcs
    
    # Paginate
    total = len(all_npcs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_npcs = all_npcs[start_idx:end_idx]
    
    # Get NPC details
    results = []
    for npc_id in page_npcs:
        npc = npc_instances.get(npc_id)
        state = scaling_manager.tiered_updates._npc_states.get(npc_id)
        
        results.append({
            "npc_id": npc_id,
            "name": npc.persona.name if npc and hasattr(npc, 'persona') else npc_id,
            "role": npc.persona.role if npc and hasattr(npc, 'persona') else "Unknown",
            "tier": state.tier if state else "unknown",
            "last_interaction": state.last_interaction if state else 0
        })
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "npcs": results
    }

@app.get("/players/paginated")
async def get_players_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get paginated list of players"""
    # Get all players from database
    conn = sqlite3.connect(str(DATABASE_PATH / "memory_vault.db"))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT player_id, player_name, total_interactions, global_reputation FROM player_sessions"
    )
    all_players = [
        {
            "player_id": row[0],
            "player_name": row[1],
            "total_interactions": row[2],
            "global_reputation": row[3]
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    
    total = len(all_players)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_players = all_players[start_idx:end_idx]
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "players": page_players
    }

@app.get("/quests/paginated")
async def get_quests_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None, description="Filter by status: available, active, completed")
):
    """Get paginated list of quests"""
    all_quests = quest_generator.get_available_quests()
    
    # Filter by status (quests are dicts, not objects)
    if status:
        all_quests = [q for q in all_quests if q["status"] == status]
    
    total = len(all_quests)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_quests = all_quests[start_idx:end_idx]
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "quests": [{
            "quest_id": q["quest_id"],
            "title": q["title"],
            "type": q["quest_type"],
            "difficulty": q["difficulty"],
            "status": q["status"]
        } for q in page_quests]
    }

# --- Performance & Scaling Endpoints ---

@app.get("/scaling/stats")
async def get_scaling_stats():
    """Get performance and scaling statistics"""
    return {
        "status": "operational",
        "stats": scaling_manager.get_system_stats(),
        "active_npcs": len(npc_instances),
        "tier_distribution": scaling_manager.tiered_updates.get_stats()
    }

@app.post("/scaling/optimize")
async def trigger_optimization():
    """Trigger optimization tasks (memory cleanup, index analysis)"""
    start_time = time.time()
    cleaned = 0
    
    try:
        # Cleanup forgotten memories
        cleaned = scaling_manager.batch_ops.batch_cleanup_memories(0.05)
    except Exception as e:
        print(f"Memory cleanup skipped: {e}")
    
    # Flush pending writes
    try:
        scaling_manager.batch_ops.flush()
    except Exception as e:
        print(f"Flush skipped: {e}")
    
    # Update tier assignments
    scaling_manager.tiered_updates.update_tiers()
    
    processing_time = time.time() - start_time
    
    return {
        "status": "optimization_complete",
        "memories_cleaned": cleaned,
        "processing_time_ms": round(processing_time * 1000, 2),
        "tier_stats": scaling_manager.tiered_updates.get_stats()
    }

@app.get("/scaling/cache")
async def get_cache_stats():
    """Get cache statistics"""
    return scaling_manager.cache.stats()

@app.post("/scaling/cache/clear")
async def clear_cache():
    """Clear all caches"""
    scaling_manager.cache.clear()
    return {"status": "cache_cleared"}

# --- Bulk Data Endpoints ---

@app.get("/bulk/npc-data")
async def get_bulk_npc_data(npc_ids: str = Query(..., description="Comma-separated NPC IDs")):
    """Get data for multiple NPCs in single request"""
    npc_id_list = [id.strip() for id in npc_ids.split(",")]
    
    # Use cached batch fetch
    cache_key = f"bulk:npc:{','.join(sorted(npc_id_list))}"
    
    def fetch_data():
        return scaling_manager.batch_ops.batch_get_npc_data(npc_id_list)
    
    data = scaling_manager.get_cached_or_fetch(cache_key, fetch_data, ttl=60)
    
    return {
        "requested": len(npc_id_list),
        "found": len(data),
        "npcs": data
    }

# --- Zone-based Processing ---

@app.post("/zone/{zone_id}/tick")
async def process_zone_tick(zone_id: str):
    """Process a tick for NPCs in a specific zone only"""
    start_time = time.time()
    
    zone_npcs = scaling_manager.tiered_updates.get_npcs_in_zone(zone_id)
    events = []
    
    for npc_id in zone_npcs:
        if npc_id in npc_instances:
            # Light processing for zone tick
            npc = npc_instances[npc_id]
            # Could trigger idle behaviors, ambient dialogue, etc.
            events.append({"npc_id": npc_id, "event": "zone_tick"})
    
    processing_time = time.time() - start_time
    
    return {
        "zone": zone_id,
        "npcs_processed": len(zone_npcs),
        "events": events,
        "processing_time_ms": round(processing_time * 1000, 2)
    }

@app.post("/zone/{zone_id}/register")
async def register_npc_to_zone(zone_id: str, npc_id: str):
    """Register an NPC to a specific zone"""
    if npc_id not in npc_instances:
        raise HTTPException(status_code=404, detail="NPC not initialized")
    
    scaling_manager.tiered_updates.register_npc(npc_id, zone_id)
    
    return {
        "status": "registered",
        "npc_id": npc_id,
        "zone": zone_id
    }

# ============================================================================
# Voice System Endpoints (Enhanced)
# ============================================================================

class VoiceGenerateRequest(BaseModel):
    """Request for voice generation"""
    text: str
    mood: str = "neutral"
    format: str = "mp3"  # "mp3" or "wav" - use "wav" for Unreal Engine

class VoiceCloneRequest(BaseModel):
    """Request for voice cloning"""
    voice_name: str
    description: str = ""
    audio_base64: List[str]  # List of base64 encoded audio files

class VoicePreviewRequest(BaseModel):
    """Request for previewing voice fingerprint"""
    role: str
    gender: str = "male"
    personality: Dict[str, float] = {}

@app.get("/voice/available")
async def get_available_voices():
    """Get all available voice profiles (library + cloned)"""
    voices = npc_voice_system_instance.get_available_voices()
    return {
        "voices": voices,
        "library_count": len([v for v in voices if v["type"] == "library"]),
        "cloned_count": len([v for v in voices if v["type"] == "cloned"])
    }

@app.get("/voice/assignments")
async def get_voice_assignments():
    """Get all NPC voice assignments with fingerprint details"""
    return {
        "assignments": npc_voice_system_instance.get_all_assignments(),
        "stats": npc_voice_system_instance.get_stats()
    }

@app.get("/voice/info/{npc_id}")
async def get_npc_voice_info(npc_id: str):
    """Get detailed voice information for a specific NPC"""
    info = npc_voice_system_instance.get_npc_voice_info(npc_id)
    if not info:
        raise HTTPException(status_code=404, detail="No voice assigned to this NPC")
    return info

@app.post("/voice/assign/{npc_id}")
async def assign_voice_to_npc(npc_id: str, voice_key: str = None):
    """
    Assign a unique voice to an NPC based on personality traits.
    If voice_key is provided, uses that as base voice.
    Otherwise, auto-assigns based on NPC characteristics.
    """
    if npc_id not in npc_instances:
        raise HTTPException(status_code=404, detail="NPC not initialized")
    
    npc = npc_instances[npc_id]
    
    # Extract NPC data
    persona = npc.persona if hasattr(npc, 'persona') else {}
    if isinstance(persona, dict):
        role = persona.get('role', 'citizen')
        gender = persona.get('gender', 'male')
        faction = persona.get('faction', 'citizens')
        personality = persona.get('personality', {})
    else:
        role = getattr(persona, 'role', 'citizen')
        gender = getattr(persona, 'gender', 'male')
        faction = getattr(persona, 'faction', 'citizens')
        personality = getattr(persona, 'personality', {})
    
    # If personality is an object, convert to dict
    if hasattr(personality, '__dict__'):
        personality = {
            'curiosity': getattr(personality, 'curiosity', 0.5),
            'empathy': getattr(personality, 'empathy', 0.5),
            'risk_tolerance': getattr(personality, 'risk_tolerance', 0.5),
            'aggression': getattr(personality, 'aggression', 0.5),
            'discipline': getattr(personality, 'discipline', 0.5),
            'romanticism': getattr(personality, 'romanticism', 0.5),
            'opportunism': getattr(personality, 'opportunism', 0.5),
            'paranoia': getattr(personality, 'paranoia', 0.5),
        }
    
    # Assign unique voice with fingerprint
    base_profile, fingerprint = npc_voice_system_instance.assign_unique_voice(
        npc_id=npc_id,
        role=role,
        gender=gender,
        faction=faction,
        personality=personality
    )
    
    return {
        "status": "assigned",
        "npc_id": npc_id,
        "voice": {
            "base_voice": fingerprint.base_voice_key,
            "voice_name": base_profile.voice_name,
            "voice_id": base_profile.voice_id,
            "description": base_profile.description
        },
        "fingerprint": {
            "pitch_description": fingerprint.pitch_description,
            "speed_mod": round(fingerprint.speed_mod, 2),
            "stability_mod": round(fingerprint.stability_mod, 3),
            "similarity_mod": round(fingerprint.similarity_mod, 3),
            "style_mod": round(fingerprint.style_mod, 3)
        }
    }

@app.post("/voice/generate/{npc_id}")
async def generate_npc_speech(npc_id: str, request: VoiceGenerateRequest):
    """
    Generate speech audio for an NPC with unique voice fingerprint.
    
    Set format="wav" for Unreal Engine compatibility.
    Returns base64 encoded audio (MP3 or WAV).
    """
    if npc_id not in npc_instances:
        raise HTTPException(status_code=404, detail="NPC not initialized")
    
    npc = npc_instances[npc_id]
    
    # Extract NPC data for voice generation
    persona = npc.persona if hasattr(npc, 'persona') else {}
    if isinstance(persona, dict):
        role = persona.get('role', 'citizen')
        personality = persona.get('personality', {})
    else:
        role = getattr(persona, 'role', 'citizen')
        personality = getattr(persona, 'personality', {})
    
    if hasattr(personality, '__dict__'):
        personality = vars(personality)
    
    # Generate speech with unique fingerprint
    audio_bytes = await npc_voice_system_instance.generate_speech_async(
        npc_id=npc_id,
        text=request.text,
        mood=request.mood,
        role=role,
        personality=personality
    )
    
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate voice audio")
    
    # Convert to WAV if requested (for Unreal Engine)
    output_format = request.format.lower()
    if output_format == "wav":
        try:
            import io
            from pydub import AudioSegment
            
            # Convert MP3 to WAV
            mp3_audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            wav_buffer = io.BytesIO()
            mp3_audio.export(wav_buffer, format="wav")
            audio_bytes = wav_buffer.getvalue()
            mime_type = "audio/wav"
        except ImportError:
            # pydub not available, return MP3 with warning
            output_format = "mp3"
            mime_type = "audio/mpeg"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"WAV conversion failed: {str(e)}")
    else:
        output_format = "mp3"
        mime_type = "audio/mpeg"
    
    # Get voice info for response
    voice_info = npc_voice_system_instance.get_npc_voice_info(npc_id)
    
    # Convert bytes to base64
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return {
        "npc_id": npc_id,
        "text": request.text,
        "mood": request.mood,
        "audio_base64": audio_b64,
        "audio_url": f"data:{mime_type};base64,{audio_b64}",
        "format": output_format,
        "voice_info": {
            "base_voice": voice_info.get("base_voice") if voice_info else None,
            "voice_name": voice_info.get("voice_name") if voice_info else None,
            "pitch_description": voice_info.get("pitch_description") if voice_info else None
        }
    }

@app.post("/voice/clone/{npc_id}")
async def clone_voice_for_npc(npc_id: str, request: VoiceCloneRequest):
    """
    Clone a custom voice from audio samples for a specific NPC.
    Requires 1-3 audio samples (base64 encoded MP3/WAV, 10-30 seconds each).
    """
    if npc_id not in npc_instances:
        raise HTTPException(status_code=404, detail="NPC not initialized")
    
    if not request.audio_base64 or len(request.audio_base64) == 0:
        raise HTTPException(status_code=400, detail="At least one audio sample is required")
    
    if len(request.audio_base64) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 audio samples allowed")
    
    # Decode audio files
    try:
        audio_files = [base64.b64decode(audio) for audio in request.audio_base64]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {str(e)}")
    
    # Clone voice
    profile = npc_voice_system_instance.clone_voice(
        npc_id=npc_id,
        audio_files=audio_files,
        voice_name=request.voice_name,
        description=request.description
    )
    
    if not profile:
        raise HTTPException(status_code=500, detail="Failed to clone voice")
    
    return {
        "status": "cloned",
        "npc_id": npc_id,
        "voice": {
            "voice_id": profile.voice_id,
            "voice_name": profile.voice_name,
            "description": profile.description,
            "is_cloned": True
        }
    }

@app.delete("/voice/clone/{npc_id}")
async def delete_cloned_voice(npc_id: str):
    """Delete a cloned voice for an NPC"""
    success = npc_voice_system_instance.delete_cloned_voice(npc_id)
    if not success:
        raise HTTPException(status_code=404, detail="No cloned voice found for this NPC")
    
    return {"status": "deleted", "npc_id": npc_id}

@app.post("/voice/preview")
async def preview_voice_fingerprint(request: VoicePreviewRequest):
    """
    Preview what voice fingerprint would be generated for given parameters.
    Useful for testing personality-to-voice mapping without creating an assignment.
    """
    preview = npc_voice_system_instance.preview_fingerprint(
        role=request.role,
        gender=request.gender,
        personality=request.personality
    )
    return preview

@app.get("/voice/stats")
async def get_voice_stats():
    """Get voice system statistics"""
    return npc_voice_system_instance.get_stats()

@app.post("/voice/reset/{npc_id}")
async def reset_npc_voice(npc_id: str):
    """Reset voice assignment for a specific NPC so it can be reassigned"""
    success = npc_voice_system_instance.reset_voice_assignment(npc_id)
    if not success:
        raise HTTPException(status_code=404, detail="No voice assignment found for this NPC")
    return {"status": "reset", "npc_id": npc_id}

@app.post("/voice/reset-all")
async def reset_all_voices():
    """Reset ALL voice assignments. Use to fix voice conflicts."""
    result = npc_voice_system_instance.reset_all_voices()
    return {"status": "reset", **result}

# ============================================================================
# Speech-to-Text Endpoints (Player Microphone Input)
# ============================================================================

class SpeechToTextRequest(BaseModel):
    """Request for speech-to-text conversion"""
    audio_base64: str  # Base64 encoded audio (webm, mp3, wav)
    language: str = "en"  # ISO-639-1 language code

@app.post("/speech/transcribe")
async def transcribe_speech(request: SpeechToTextRequest):
    """
    Transcribe player speech to text using OpenAI Whisper.
    Accepts base64 encoded audio (webm, mp3, wav, m4a).
    """
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio_base64)
        
        # Check file size (max 25MB)
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")
        
        # Create file-like object
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.webm"  # Whisper needs a filename with extension
        
        # Transcribe using Whisper
        response = await stt_client.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="json",
            language=request.language
        )
        
        return {
            "status": "success",
            "text": response.text,
            "language": request.language
        }
        
    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/speech/transcribe-file")
async def transcribe_speech_file(
    file: UploadFile = File(...),
    language: str = "en"
):
    """
    Transcribe uploaded audio file to text.
    Supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
    """
    try:
        # Read file content
        audio_data = await file.read()
        
        # Check file size
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")
        
        # Create file-like object with original filename
        audio_file = io.BytesIO(audio_data)
        audio_file.name = file.filename or "audio.webm"
        
        # Transcribe
        response = await stt_client.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="json",
            language=language
        )
        
        return {
            "status": "success",
            "text": response.text,
            "filename": file.filename,
            "language": language
        }
        
    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/speech/interact/{npc_id}")
async def voice_interact_with_npc(
    npc_id: str,
    request: SpeechToTextRequest,
    player_id: str = "default_player",
    player_name: str = "Traveler"
):
    """
    Complete voice interaction: Transcribe player speech -> NPC response -> Generate NPC voice.
    Returns both transcribed text and NPC audio response.
    """
    if npc_id not in npc_instances:
        raise HTTPException(status_code=404, detail="NPC not initialized")
    
    try:
        # Step 1: Transcribe player speech
        audio_data = base64.b64decode(request.audio_base64)
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.webm"
        
        transcription = await stt_client.transcribe(
            file=audio_file,
            model="whisper-1",
            response_format="json",
            language=request.language
        )
        
        player_text = transcription.text
        
        if not player_text.strip():
            return {
                "status": "empty_transcription",
                "player_text": "",
                "npc_response": None
            }
        
        # Step 2: Get NPC response
        npc = npc_instances[npc_id]
        player = player_manager.get_or_create_player(player_id, player_name)
        
        # Process action
        response = await npc.process_player_action(player_text)
        cognitive_frame = response.get("cognitive_frame", {})
        npc_dialogue = cognitive_frame.get("dialogue", "")
        mood = cognitive_frame.get("emotional_state", "neutral")
        
        # Step 3: Generate NPC voice response
        npc_audio_b64 = None
        voice_info = None
        
        if npc_dialogue:
            # Get voice info
            voice_info = npc_voice_system_instance.get_npc_voice_info(npc_id)
            
            # Generate speech
            audio_bytes = await npc_voice_system_instance.generate_speech_async(
                npc_id=npc_id,
                text=npc_dialogue[:500],
                mood=mood
            )
            
            if audio_bytes:
                npc_audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        return {
            "status": "success",
            "player_text": player_text,
            "npc_response": {
                "dialogue": npc_dialogue,
                "mood": mood,
                "inner_thoughts": cognitive_frame.get("internal_reflection"),
                "audio_url": f"data:audio/mpeg;base64,{npc_audio_b64}" if npc_audio_b64 else None,
                "voice_info": voice_info
            }
        }
        
    except Exception as e:
        print(f"Voice interaction error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice interaction failed: {str(e)}")

# ============================================================================
# WebSocket Endpoint for Real-Time Game Communication
# ============================================================================

def get_ws_handler() -> WebSocketHandler:
    """Get or create the WebSocket handler with all dependencies"""
    global ws_handler
    if ws_handler is None:
        ws_handler = WebSocketHandler(
            npc_instances=npc_instances,
            npc_voice_system=npc_voice_system_instance,
            stt_client=stt_client,
            world_simulator=world_simulator,
            faction_system=faction_system,
            territory_system=territory_system,
            quest_generator=quest_generator,
            conversation_manager=conversation_manager
        )
        # Ensure conversation manager has NPC instances and voice system reference
        conversation_manager.set_npc_instances(npc_instances)
        conversation_manager.set_voice_system(npc_voice_system_instance)
        # Set conversation manager on handler
        ws_handler.set_conversation_manager(conversation_manager)
    return ws_handler

@app.websocket("/ws/game")
async def websocket_game_endpoint(websocket: WebSocket, player_id: str = "default_player", player_name: str = "Traveler"):
    """
    WebSocket endpoint for real-time game communication.
    
    Connect: ws://{host}/ws/game?player_id=xxx&player_name=PlayerName
    
    Message Types (Client -> Server):
        - ping: Keep-alive { "type": "ping" }
        - npc_init: Initialize NPC { "type": "npc_init", "npc_id": "vera" }
        - npc_action: NPC dialogue { "type": "npc_action", "npc_id": "vera", "action": "Hello" }
        - npc_status: Get NPC status { "type": "npc_status", "npc_id": "vera" }
        - voice_generate: Generate TTS { "type": "voice_generate", "npc_id": "vera", "text": "..." }
        - speech_transcribe: STT { "type": "speech_transcribe", "audio_base64": "..." }
        - subscribe_events: Subscribe { "type": "subscribe_events", "events": ["world_events"] }
        - get_factions: Get factions { "type": "get_factions" }
        - get_world_events: Get events { "type": "get_world_events", "limit": 10 }
        
        Multi-NPC Conversation Groups:
        - update_location: Update location { "type": "update_location", "entity_type": "npc|player", "entity_id": "...", "x": 0, "y": 0, "z": 0, "zone": "area" }
        - get_nearby_npcs: Find nearby NPCs { "type": "get_nearby_npcs", "max_distance": 500 }
        - start_conversation: Start group chat { "type": "start_conversation", "npc_ids": ["npc1"], "location": "area", "auto_discover": true }
        - conversation_message: Send message { "type": "conversation_message", "group_id": "...", "message": "...", "target_npc_id": "..." }
        - add_npc_to_conversation: Add NPC { "type": "add_npc_to_conversation", "group_id": "...", "npc_id": "..." }
        - remove_npc_from_conversation: Remove NPC { "type": "remove_npc_from_conversation", "group_id": "...", "npc_id": "..." }
        - end_conversation: End chat { "type": "end_conversation", "group_id": "..." }
        - get_conversation: Get state { "type": "get_conversation", "group_id": "..." }
    
    All responses include 'type' and 'timestamp' fields.
    Include 'request_id' in your message to correlate responses.
    """
    # Accept connection
    client = await ws_manager.connect(websocket, player_id, player_name)
    handler = get_ws_handler()
    
    # Send connected confirmation
    await ws_manager.send_message(player_id, {
        "type": MessageType.CONNECTED,
        "player_id": player_id,
        "player_name": player_name,
        "active_npcs": list(npc_instances.keys()),
        "message": "Connected to Fractured Survival NPC Service",
        "timestamp": __import__('time').time()
    })
    
    print(f"[WebSocket] Client connected: {player_id} ({player_name})")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Handle message
            response = await handler.handle_message(client, data)
            
            # Send response if any (voice_generate sends its own responses)
            if response:
                await ws_manager.send_message(player_id, response)
                
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: {player_id}")
        ws_manager.disconnect(player_id)
    except Exception as e:
        print(f"[WebSocket] Error for {player_id}: {e}")
        ws_manager.disconnect(player_id)

@app.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "active_connections": ws_manager.get_connection_count(),
        "event_subscribers": {
            k: len(v) for k, v in ws_manager.event_subscribers.items()
        },
        "handler_ready": ws_handler is not None
    }

# ============================================================================
# Multi-NPC Conversation Groups API
# ============================================================================

class UpdateLocationRequest(BaseModel):
    """Update NPC or player location from Unreal Engine"""
    x: float
    y: float
    z: float
    zone: str = "unknown"

class StartConversationRequest(BaseModel):
    """Request to start a group conversation"""
    player_id: str
    player_name: str = "Traveler"
    npc_ids: Optional[List[str]] = None  # If None, auto-discover nearby NPCs
    location: str = "unknown"
    auto_discover: bool = True

class ConversationMessageRequest(BaseModel):
    """Request to send a message in a group conversation"""
    message: str
    target_npc_id: Optional[str] = None  # Direct message to specific NPC
    with_voice: bool = False  # If True, generate TTS for each NPC response
    voice_format: str = "wav"  # Audio format: "wav" or "mp3"

class AddNPCToConversationRequest(BaseModel):
    """Request to add an NPC to existing conversation"""
    npc_id: str

# Initialize conversation manager with NPC instances on first use
@app.on_event("startup")
async def init_conversation_manager():
    """Initialize conversation manager with NPC instances reference"""
    # This will be called when the app starts
    # The actual NPC instances will be set when NPCs are initialized
    pass

def ensure_conversation_manager_initialized():
    """Ensure conversation manager has access to NPC instances and voice system"""
    conversation_manager.set_npc_instances(npc_instances)
    conversation_manager.set_voice_system(npc_voice_system_instance)

@app.post("/conversation/location/npc/{npc_id}")
async def update_npc_location(npc_id: str, request: UpdateLocationRequest):
    """
    Update NPC location from Unreal Engine.
    Call this when NPC moves in the game world.
    """
    conversation_manager.update_npc_location(
        npc_id=npc_id,
        x=request.x,
        y=request.y,
        z=request.z,
        zone=request.zone
    )
    return {
        "status": "updated",
        "npc_id": npc_id,
        "location": {"x": request.x, "y": request.y, "z": request.z, "zone": request.zone}
    }

@app.post("/conversation/location/player/{player_id}")
async def update_player_location(player_id: str, request: UpdateLocationRequest):
    """
    Update player location from Unreal Engine.
    Call this when player moves in the game world.
    """
    conversation_manager.update_player_location(
        player_id=player_id,
        x=request.x,
        y=request.y,
        z=request.z,
        zone=request.zone
    )
    return {
        "status": "updated",
        "player_id": player_id,
        "location": {"x": request.x, "y": request.y, "z": request.z, "zone": request.zone}
    }

@app.post("/conversation/location/batch")
async def update_locations_batch(locations: List[Dict]):
    """
    Batch update multiple NPC/player locations.
    Each item: {"id": "npc_id", "type": "npc"|"player", "x": 0, "y": 0, "z": 0, "zone": "area"}
    """
    updated = 0
    for loc in locations:
        entity_id = loc.get("id")
        entity_type = loc.get("type", "npc")
        x = loc.get("x", 0)
        y = loc.get("y", 0)
        z = loc.get("z", 0)
        zone = loc.get("zone", "unknown")
        
        if entity_type == "player":
            conversation_manager.update_player_location(entity_id, x, y, z, zone)
        else:
            conversation_manager.update_npc_location(entity_id, x, y, z, zone)
        updated += 1
    
    return {"status": "batch_updated", "count": updated}

@app.get("/conversation/nearby/{player_id}")
async def get_nearby_npcs(player_id: str, max_distance: float = None):
    """
    Get NPCs near the player based on location data.
    Returns list of NPC IDs that could join a conversation.
    """
    ensure_conversation_manager_initialized()
    nearby = conversation_manager.get_nearby_npcs(player_id, max_distance)
    
    # Get NPC details
    npc_details = []
    for npc_id in nearby:
        if npc_id in npc_instances:
            npc = npc_instances[npc_id]
            persona = npc.persona if hasattr(npc, 'persona') else {}
            name = persona.get("name", npc_id) if isinstance(persona, dict) else npc_id
            role = persona.get("role", "Unknown") if isinstance(persona, dict) else "Unknown"
            
            loc = conversation_manager.npc_locations.get(npc_id)
            npc_details.append({
                "npc_id": npc_id,
                "name": name,
                "role": role,
                "location": {
                    "x": loc.x if loc else 0,
                    "y": loc.y if loc else 0,
                    "z": loc.z if loc else 0,
                    "zone": loc.zone if loc else "unknown"
                } if loc else None
            })
    
    return {
        "player_id": player_id,
        "nearby_npcs": npc_details,
        "count": len(npc_details)
    }

@app.post("/conversation/start")
async def start_group_conversation(request: StartConversationRequest):
    """
    Start a new multi-NPC group conversation.
    
    If npc_ids provided, uses those specific NPCs.
    If auto_discover=True and npc_ids not provided, finds NPCs near the player.
    """
    ensure_conversation_manager_initialized()
    
    try:
        group = await conversation_manager.start_group_conversation(
            player_id=request.player_id,
            player_name=request.player_name,
            npc_ids=request.npc_ids,
            location=request.location,
            auto_discover=request.auto_discover
        )
        
        # Get participant details
        participants = []
        for npc_id, participant in group.participants.items():
            if npc_id in npc_instances:
                npc = npc_instances[npc_id]
                persona = npc.persona if hasattr(npc, 'persona') else {}
                name = persona.get("name", npc_id) if isinstance(persona, dict) else npc_id
                role = persona.get("role", "Unknown") if isinstance(persona, dict) else "Unknown"
                
                participants.append({
                    "npc_id": npc_id,
                    "name": name,
                    "role": role,
                    "mood": participant.mood
                })
        
        return {
            "status": "started",
            "group_id": group.group_id,
            "location": group.location,
            "participants": participants,
            "message": f"Group conversation started with {len(participants)} NPCs"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation/{group_id}/message")
async def send_conversation_message(group_id: str, request: ConversationMessageRequest):
    """
    Send a message in a group conversation.
    
    Returns responses from one or more NPCs based on conversation dynamics.
    NPCs may agree, disagree, elaborate, or interrupt based on their personalities.
    
    Set with_voice=True to generate TTS audio for each NPC response.
    """
    ensure_conversation_manager_initialized()
    
    try:
        responses = await conversation_manager.process_player_message(
            group_id=group_id,
            message=request.message,
            target_npc_id=request.target_npc_id
        )
        
        # Format responses
        formatted_responses = []
        for resp in responses:
            formatted_responses.append({
                "npc_id": resp.speaker_id,
                "npc_name": resp.speaker_name,
                "dialogue": resp.content,
                "response_type": resp.response_type.value if isinstance(resp.response_type, ResponseType) else resp.response_type,
                "target": resp.target_id,
                "mood": resp.mood,
                "inner_thoughts": resp.inner_thoughts,
                "timestamp": resp.timestamp
            })
        
        # Get updated group state
        group = conversation_manager.get_conversation(group_id)
        
        result = {
            "status": "processed",
            "group_id": group_id,
            "responses": formatted_responses,
            "response_count": len(formatted_responses),
            "tension_level": group.tension_level if group else 0,
            "topic": group.topic if group else "general"
        }
        
        # Generate voice if requested
        if request.with_voice and responses:
            voice_results = await conversation_manager.generate_voice_for_responses(
                responses, 
                audio_format=request.voice_format
            )
            result["voice_responses"] = voice_results
            result["voice_format"] = request.voice_format
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation/{group_id}/add-npc")
async def add_npc_to_conversation(group_id: str, request: AddNPCToConversationRequest):
    """Add an NPC to an existing group conversation"""
    ensure_conversation_manager_initialized()
    
    success = await conversation_manager.add_npc_to_conversation(group_id, request.npc_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Could not add NPC to conversation")
    
    group = conversation_manager.get_conversation(group_id)
    return {
        "status": "added",
        "group_id": group_id,
        "npc_id": request.npc_id,
        "total_participants": len(group.participants) if group else 0
    }

@app.post("/conversation/{group_id}/remove-npc/{npc_id}")
async def remove_npc_from_conversation(group_id: str, npc_id: str):
    """Remove an NPC from a group conversation"""
    ensure_conversation_manager_initialized()
    
    success = await conversation_manager.remove_npc_from_conversation(group_id, npc_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Could not remove NPC from conversation")
    
    return {
        "status": "removed",
        "group_id": group_id,
        "npc_id": npc_id
    }

@app.post("/conversation/{group_id}/end")
async def end_conversation(group_id: str):
    """End a group conversation"""
    ensure_conversation_manager_initialized()
    
    group = conversation_manager.end_conversation(group_id)
    
    if not group:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "status": "ended",
        "group_id": group_id,
        "duration_seconds": time.time() - group.started_at,
        "total_messages": len(group.history),
        "final_tension": group.tension_level
    }

@app.get("/conversation/stats")
async def get_conversation_stats():
    """Get conversation system statistics"""
    ensure_conversation_manager_initialized()
    return conversation_manager.get_stats()

@app.post("/conversation/cleanup")
async def cleanup_expired_conversations():
    """Remove expired conversations"""
    ensure_conversation_manager_initialized()
    expired = conversation_manager.cleanup_expired_conversations()
    return {"status": "cleanup_complete", "expired_count": expired}

@app.get("/conversation/player/{player_id}/active")
async def get_player_active_conversations(player_id: str):
    """Get all active conversations for a player"""
    ensure_conversation_manager_initialized()
    
    conversations = conversation_manager.get_player_conversations(player_id)
    
    return {
        "player_id": player_id,
        "conversations": [
            {
                "group_id": g.group_id,
                "location": g.location,
                "participants": list(g.participants.keys()),
                "is_active": g.is_active
            }
            for g in conversations
        ],
        "count": len(conversations)
    }

@app.get("/conversation/{group_id}")
async def get_conversation_state(group_id: str):
    """Get current state of a group conversation"""
    ensure_conversation_manager_initialized()
    
    group = conversation_manager.get_conversation(group_id)
    
    if not group:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get participant details
    participants = []
    for npc_id, participant in group.participants.items():
        participants.append({
            "npc_id": npc_id,
            "role": participant.role.value,
            "mood": participant.mood,
            "statements_count": participant.statements_count,
            "attention_level": participant.attention_level
        })
    
    # Get recent history
    history = []
    for msg in group.history[-10:]:
        history.append({
            "speaker_id": msg.speaker_id,
            "speaker_name": msg.speaker_name,
            "content": msg.content,
            "response_type": msg.response_type.value if isinstance(msg.response_type, ResponseType) else msg.response_type,
            "timestamp": msg.timestamp
        })
    
    return {
        "group_id": group.group_id,
        "player_id": group.player_id,
        "player_name": group.player_name,
        "location": group.location,
        "is_active": group.is_active,
        "topic": group.topic,
        "tension_level": group.tension_level,
        "participants": participants,
        "recent_history": history,
        "started_at": group.started_at,
        "last_activity": group.last_activity
    }

@app.get("/conversation/player/{player_id}/active")
async def get_player_active_conversations(player_id: str):
    """Get all active conversations for a player"""
    ensure_conversation_manager_initialized()
    
    conversations = conversation_manager.get_player_conversations(player_id)
    
    return {
        "player_id": player_id,
        "conversations": [
            {
                "group_id": g.group_id,
                "location": g.location,
                "participants": list(g.participants.keys()),
                "is_active": g.is_active
            }
            for g in conversations
        ],
        "count": len(conversations)
    }

# Main
if __name__ == "__main__":
    print("\n" + "="*70)
    print("FRACTURED SURVIVAL - STANDALONE NPC SERVICE")
    print("="*70)
    print("\nStarting on http://0.0.0.0:9000")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
