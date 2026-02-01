"""FastAPI Bridge for NPC System - Phase 2: Engine Integration"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import sys
import os

# Add NPC system to path
sys.path.insert(0, '/app/npc_system')

from core.npc_system import NPCSystem

# Router for NPC endpoints
npc_router = APIRouter(prefix="/npc", tags=["npc"])

# Global NPC instances (in-memory for now)
npc_instances: Dict[str, NPCSystem] = {}
npc_tasks: Dict[str, asyncio.Task] = {}

# Import multi-NPC orchestrator
sys.path.insert(0, '/app/npc_system')
from core.multi_npc import orchestrator

# Request/Response Models
class NPCInitRequest(BaseModel):
    npc_id: str
    persona_file: Optional[str] = None

class PlayerActionRequest(BaseModel):
    npc_id: str
    action: str

class NPCResponse(BaseModel):
    cognitive_frame: Dict
    limbic_state: Dict
    personality_snapshot: Dict

class NPCStatusResponse(BaseModel):
    npc_id: str
    active: bool
    vitals: Dict
    emotional_state: Dict
    personality: Dict

# Initialize NPC
@npc_router.post("/init")
async def initialize_npc(request: NPCInitRequest):
    """Initialize an NPC instance"""
    try:
        npc_id = request.npc_id
        
        # Check if already exists
        if npc_id in npc_instances:
            return {"status": "already_exists", "npc_id": npc_id}
        
        # Determine persona file
        if request.persona_file:
            persona_path = f"/app/npc_system/persona/{request.persona_file}"
        else:
            # Default persona based on ID
            persona_map = {
                "vera": "vera_v1.json",
                "guard": "guard_v1.json",
                "merchant": "merchant_v1.json"
            }
            persona_file = persona_map.get(npc_id.lower(), "vera_v1.json")
            persona_path = f"/app/npc_system/persona/{persona_file}"
        
        # Create NPC instance
        npc = NPCSystem(persona_path)
        npc_instances[npc_id] = npc
        
        # Register with orchestrator
        faction_map = {
            "vera": "guards",
            "guard": "guards",
            "merchant": "traders"
        }
        faction = faction_map.get(npc_id.lower(), "citizens")
        orchestrator.register_npc(npc_id, npc, faction)
        
        # Start autonomous systems in background
        task = asyncio.create_task(npc.start_autonomous_systems())
        npc_tasks[npc_id] = task
        
        return {
            "status": "initialized",
            "npc_id": npc_id,
            "persona": npc.persona["role"],
            "location": npc.persona["location"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize NPC: {str(e)}")

# Process player action
@npc_router.post("/action", response_model=NPCResponse)
async def process_action(request: PlayerActionRequest):
    """Send player action to NPC and get response"""
    try:
        npc_id = request.npc_id
        
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail=f"NPC '{npc_id}' not found. Initialize first.")
        
        npc = npc_instances[npc_id]
        response = await npc.process_player_action(request.action)
        
        return NPCResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing action: {str(e)}")

# Get NPC status
@npc_router.get("/status/{npc_id}", response_model=NPCStatusResponse)
async def get_npc_status(npc_id: str):
    """Get current status of an NPC"""
    try:
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail=f"NPC '{npc_id}' not found")
        
        npc = npc_instances[npc_id]
        limbic_state = npc.limbic.get_state_summary()
        
        return NPCStatusResponse(
            npc_id=npc_id,
            active=True,
            vitals=limbic_state["vitals"],
            emotional_state=limbic_state["emotional_state"],
            personality=npc.personality
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get NPC memories
@npc_router.get("/memories/{npc_id}")
async def get_npc_memories(npc_id: str, limit: int = 5):
    """Get recent memories of an NPC"""
    try:
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail=f"NPC '{npc_id}' not found")
        
        npc = npc_instances[npc_id]
        memories = npc.memory_vault.get_recent_memories(npc_id, limit=limit)
        
        return {
            "npc_id": npc_id,
            "memories": [
                {
                    "type": m.memory_type,
                    "content": m.content,
                    "strength": m.strength,
                    "timestamp": m.timestamp
                }
                for m in memories
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get NPC beliefs
@npc_router.get("/beliefs/{npc_id}")
async def get_npc_beliefs(npc_id: str, limit: int = 5):
    """Get summary beliefs of an NPC"""
    try:
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail=f"NPC '{npc_id}' not found")
        
        npc = npc_instances[npc_id]
        beliefs = npc.memory_vault.get_summary_beliefs(npc_id, limit=limit)
        
        return {
            "npc_id": npc_id,
            "beliefs": beliefs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List active NPCs


# Phase 3: Multi-NPC Endpoints

@npc_router.post("/interact")
async def npc_to_npc_interaction(from_npc: str, to_npc: str, action: str):
    """Facilitate interaction between two NPCs"""
    try:
        result = await orchestrator.npc_to_npc_interaction(from_npc, to_npc, action)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@npc_router.get("/factions")
async def get_factions():
    """Get faction status"""
    try:
        return orchestrator.get_faction_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@npc_router.get("/trust/{npc1}/{npc2}")
async def get_trust_level(npc1: str, npc2: str):
    """Get trust level between two NPCs"""
    try:
        trust = orchestrator.get_trust(npc1, npc2)
        return {"from": npc1, "to": npc2, "trust": trust}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@npc_router.get("/list")
async def list_npcs():
    """List all active NPC instances"""
    npcs = []
    for npc_id, npc in npc_instances.items():
        npcs.append({
            "npc_id": npc_id,
            "role": npc.persona["role"],
            "location": npc.persona["location"],
            "mood": npc.limbic.emotional_state.mood
        })
    return {"npcs": npcs}

# Shutdown NPC
@npc_router.post("/shutdown/{npc_id}")
async def shutdown_npc(npc_id: str):
    """Shutdown an NPC instance"""
    try:
        if npc_id not in npc_instances:
            raise HTTPException(status_code=404, detail=f"NPC '{npc_id}' not found")
        
        npc = npc_instances[npc_id]
        npc.stop()
        
        # Cancel autonomous task
        if npc_id in npc_tasks:
            npc_tasks[npc_id].cancel()
            del npc_tasks[npc_id]
        
        del npc_instances[npc_id]
        
        return {"status": "shutdown", "npc_id": npc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
