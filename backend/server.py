from fastapi import FastAPI, APIRouter, HTTPException, Request, Header, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import websockets
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import httpx

# Import MongoDB auth system
from auth_mongo import AuthSystemMongo

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Also load NPC system env for voice/LLM keys
load_dotenv("/app/npc_system/.env")

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'npc_system')]

# Initialize auth system
auth_system = AuthSystemMongo(db)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)

# Try to import and mount NPC service directly (for deployment)
NPC_SERVICE_EMBEDDED = False
try:
    sys.path.insert(0, '/app/npc_system')
    from npc_service import app as npc_app
    NPC_SERVICE_EMBEDDED = True
    logging.info("NPC service embedded successfully")
except Exception as e:
    logging.warning(f"Could not embed NPC service, will use proxy mode: {e}")

# NPC Service URL - used only if embedded mode fails
NPC_SERVICE_URL = os.environ.get("NPC_SERVICE_URL", "http://localhost:9000")

# Mount NPC service if embedded successfully
if NPC_SERVICE_EMBEDDED:
    app.mount("/npc-direct", npc_app)
    logging.info("NPC service mounted at /npc-direct")

# Helper function to get the correct NPC service base URL
def get_npc_base_url():
    """Returns the base URL for NPC service - uses embedded if available"""
    if NPC_SERVICE_EMBEDDED:
        return "http://localhost:8001/npc-direct"
    return NPC_SERVICE_URL if NPC_SERVICE_URL.startswith("http") else f"http://{NPC_SERVICE_URL}"

# Health check endpoint (required for Kubernetes)
@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes"""
    return {"status": "healthy", "service": "npc-backend", "npc_embedded": NPC_SERVICE_EMBEDDED, "npc_service_url": NPC_SERVICE_URL}

@app.get("/")
async def root_health():
    """Root health check"""
    return {"status": "ok", "service": "Fractured Survival NPC Backend"}


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def api_root():
    return {"message": "Fractured Survival NPC API"}

@api_router.get("/health")
async def api_health():
    """API health check"""
    return {"status": "healthy", "npc_embedded": NPC_SERVICE_EMBEDDED, "npc_service_url": NPC_SERVICE_URL}

@api_router.post("/status", response_model=StatusCheck)
async def status(status: StatusCheck):
    return status

# Proxy to NPC service (or use embedded service)
@api_router.api_route("/npc/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_npc_service(path: str, request: Request):
    """Proxy all /api/npc/* requests to the NPC service"""
    # If NPC service is embedded, use internal routing
    if NPC_SERVICE_EMBEDDED:
        try:
            url = f"http://localhost:8001/npc-direct/npc/{path}"
            async with httpx.AsyncClient(timeout=60.0) as http_client:
                body = await request.body()
                # Filter headers to avoid issues
                headers = {"content-type": request.headers.get("content-type", "application/json")}
                response = await http_client.request(
                    method=request.method,
                    url=url,
                    content=body,
                    headers=headers,
                    params=request.query_params
                )
                return JSONResponse(
                    content=response.json(),
                    status_code=response.status_code
                )
        except Exception as e:
            logging.error(f"Embedded NPC service error: {e}")
            return JSONResponse(
                content={"error": f"NPC service error: {str(e)}"},
                status_code=500
            )
    
    # Fallback to external proxy
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Get request body if present
            body = await request.body()
            
            # Forward the request to NPC service
            url = f"{get_npc_base_url()}/npc/{path}"
            response = await http_client.request(
                method=request.method,
                url=url,
                content=body,
                headers=dict(request.headers),
                params=request.query_params
            )
            
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
    except httpx.ConnectError:
        return JSONResponse(
            content={"error": "NPC service not available. Please start it with: cd /app/npc_system && python3 npc_service.py"},
            status_code=503
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@api_router.get("/quests/available")
async def proxy_quests_available():
    """Proxy quests available endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/quests/available")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/quest/{path:path}")
async def proxy_quest(path: str, request: Request):
    """Proxy quest endpoints"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{get_npc_base_url()}/quest/{path}"
            response = await client.get(url, params=request.query_params)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/quest/{path:path}")
async def proxy_quest_post(path: str, request: Request):
    """Proxy quest POST endpoints"""
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{get_npc_base_url()}/quest/{path}"
            response = await client.post(url, content=body, headers=dict(request.headers))
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/territory/{path:path}")
async def proxy_territory(path: str, request: Request):
    """Proxy territory endpoints"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{get_npc_base_url()}/territory/{path}"
            response = await client.get(url, params=request.query_params)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/factions")
async def proxy_factions():
    """Proxy factions endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/factions")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/player/{player_id}")
async def proxy_player_info(player_id: str):
    """Proxy player info endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/player/{player_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/players")
async def proxy_players_list():
    """Proxy players list endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/players")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/npc/memories/{npc_id}/{player_id}")
async def proxy_npc_memories(npc_id: str, player_id: str):
    """Proxy NPC memories about player endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/npc/memories/{npc_id}/{player_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/npc/share-memories/{from_npc}/{to_npc}")
async def proxy_share_memories(from_npc: str, to_npc: str, player_id: str = None):
    """Proxy NPC memory sharing endpoint"""
    try:
        url = f"{get_npc_base_url()}/npc/share-memories/{from_npc}/{to_npc}"
        if player_id:
            url += f"?player_id={player_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/npc/heard-about/{npc_id}/{player_id}")
async def proxy_heard_about(npc_id: str, player_id: str):
    """Proxy what NPC heard about player from others"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/npc/heard-about/{npc_id}/{player_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Memory Decay Endpoints
@api_router.post("/memory/decay")
async def proxy_memory_decay(hours: float = 24.0):
    """Apply memory decay"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/memory/decay?hours={hours}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/memory/status")
async def proxy_memory_status(player_id: str = None, npc_id: str = None):
    """Get memory status"""
    try:
        params = []
        if player_id:
            params.append(f"player_id={player_id}")
        if npc_id:
            params.append(f"npc_id={npc_id}")
        query = "?" + "&".join(params) if params else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/memory/status{query}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Quest Generation Endpoints
@api_router.post("/quest/generate/{npc_id}")
async def proxy_generate_quest(npc_id: str, player_id: str = None):
    """Generate personalized quest"""
    try:
        query = f"?player_id={player_id}" if player_id else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/quest/generate/{npc_id}{query}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/quest/accept/{quest_id}")
async def proxy_accept_quest(quest_id: str, player_id: str):
    """Accept a quest"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/quest/accept/{quest_id}?player_id={player_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/quest/complete/{quest_id}")
async def proxy_complete_quest(quest_id: str):
    """Complete a quest"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/quest/complete/{quest_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# World Simulation Endpoints
@api_router.post("/world/start")
async def proxy_start_world(time_scale: float = 1.0, tick_interval: int = 60):
    """Start world simulation"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/world/start?time_scale={time_scale}&tick_interval={tick_interval}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/world/stop")
async def proxy_stop_world():
    """Stop world simulation"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/world/stop")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/world/status")
async def proxy_world_status():
    """Get world simulation status"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/world/status")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/world/tick")
async def proxy_world_tick():
    """Manual world tick"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/world/tick")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/world/events")
async def proxy_world_events(limit: int = 20):
    """Get world events"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/world/events?limit={limit}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Faction Endpoints
@api_router.get("/factions")
async def proxy_get_factions():
    """Get all factions"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/factions")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/faction/{faction_id}")
async def proxy_get_faction(faction_id: str):
    """Get faction details"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/faction/{faction_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/faction/relation/{faction1}/{faction2}")
async def proxy_faction_relation(faction1: str, faction2: str):
    """Get relation between factions"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/faction/relation/{faction1}/{faction2}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/faction/event")
async def proxy_faction_event(event_type: str = "skirmish", faction1: str = None, faction2: str = None, description: str = "Faction event"):
    """Trigger faction event"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/faction/event",
                params={"event_type": event_type, "faction1": faction1, "faction2": faction2, "description": description}
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/faction/events")
async def proxy_faction_events(limit: int = 10):
    """Get faction events"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/faction/events?limit={limit}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/player/{player_id}/factions")
async def proxy_player_factions(player_id: str):
    """Get player faction reputations"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/player/{player_id}/factions")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# Phase 4: Dynamic Civilizations Proxy Endpoints
# ============================================================================

# --- NPC Goals ---
@api_router.post("/npc/{npc_id}/goal/generate")
async def proxy_generate_goal(npc_id: str, faction: str = "citizens"):
    """Generate an autonomous goal for an NPC"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/npc/{npc_id}/goal/generate?faction={faction}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/npc/{npc_id}/goals")
async def proxy_get_npc_goals(npc_id: str, status: str = None):
    """Get all goals for an NPC"""
    try:
        query = f"?status={status}" if status else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/npc/{npc_id}/goals{query}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/goal/{goal_id}/progress")
async def proxy_update_goal_progress(goal_id: str, delta: float = 0.1):
    """Update progress on a goal"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/goal/{goal_id}/progress?delta={delta}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/goal/{goal_id}/abandon")
async def proxy_abandon_goal(goal_id: str):
    """Abandon a goal"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/goal/{goal_id}/abandon")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# --- Quest Chains ---
@api_router.post("/questchain/create/{npc_id}")
async def proxy_create_quest_chain(npc_id: str, faction: str = "citizens", player_id: str = None):
    """Create a new quest chain"""
    try:
        params = f"?faction={faction}"
        if player_id:
            params += f"&player_id={player_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/questchain/create/{npc_id}{params}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/questchains")
async def proxy_get_quest_chains(player_id: str = None):
    """Get available quest chains"""
    try:
        query = f"?player_id={player_id}" if player_id else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/questchains{query}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/questchain/{chain_id}/start")
async def proxy_start_quest_chain(chain_id: str, player_id: str):
    """Start a quest chain"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/questchain/{chain_id}/start?player_id={player_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/questchain/{chain_id}/advance")
async def proxy_advance_quest_chain(chain_id: str):
    """Advance to next quest in chain"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/questchain/{chain_id}/advance")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# --- Trade Routes ---
@api_router.post("/traderoute/establish")
async def proxy_establish_trade_route(from_npc: str, to_npc: str, from_loc: str = None, to_loc: str = None):
    """Establish a new trade route"""
    try:
        params = f"?from_npc={from_npc}&to_npc={to_npc}"
        if from_loc:
            params += f"&from_loc={from_loc}"
        if to_loc:
            params += f"&to_loc={to_loc}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/traderoute/establish{params}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/traderoutes")
async def proxy_get_trade_routes(status: str = None):
    """Get all trade routes"""
    try:
        query = f"?status={status}" if status else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/traderoutes{query}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/traderoute/{route_id}/execute")
async def proxy_execute_trade(route_id: str):
    """Execute a trade on a route"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/traderoute/{route_id}/execute")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/traderoute/{route_id}/disrupt")
async def proxy_disrupt_trade_route(route_id: str, reason: str = "attack"):
    """Disrupt a trade route"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/traderoute/{route_id}/disrupt?reason={reason}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/traderoute/{route_id}/restore")
async def proxy_restore_trade_route(route_id: str):
    """Restore a disrupted trade route"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/traderoute/{route_id}/restore")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# --- Territorial Conflicts ---
@api_router.get("/territory/control")
async def proxy_get_territory_control():
    """Get current territory control status"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/territory/control")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/territory/{territory}/battle")
async def proxy_initiate_battle(territory: str, attacker_faction: str):
    """Initiate a battle for territory"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/territory/{territory}/battle?attacker_faction={attacker_faction}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/battle/{battle_id}/resolve")
async def proxy_resolve_battle(battle_id: str):
    """Resolve a territorial battle"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/battle/{battle_id}/resolve")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/battles")
async def proxy_get_battles(territory: str = None, limit: int = 10):
    """Get battle history"""
    try:
        params = f"?limit={limit}"
        if territory:
            params += f"&territory={territory}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/battles{params}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# --- World Advancement (for Unreal Engine) ---
@api_router.post("/world/advance/{hours}")
async def proxy_advance_world(hours: float):
    """Advance the world state by specified hours (main API for Unreal Engine)"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{get_npc_base_url()}/world/advance/{hours}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# Phase 5: Scaling & Performance Proxy Endpoints
# ============================================================================

@api_router.post("/batch/interact")
async def proxy_batch_interact(request: dict):
    """Process multiple NPC interactions in a single request"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{get_npc_base_url()}/batch/interact", json=request)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/batch/init")
async def proxy_batch_init(request: dict):
    """Initialize multiple NPCs in a single request"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{get_npc_base_url()}/batch/init", json=request)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/npc/list/paginated")
async def proxy_npcs_paginated(page: int = 1, page_size: int = 20, tier: str = None):
    """Get paginated list of NPCs"""
    try:
        params = f"?page={page}&page_size={page_size}"
        if tier:
            params += f"&tier={tier}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/npc/list/paginated{params}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/players/paginated")
async def proxy_players_paginated(page: int = 1, page_size: int = 20):
    """Get paginated list of players"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/players/paginated?page={page}&page_size={page_size}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/quests/paginated")
async def proxy_quests_paginated(page: int = 1, page_size: int = 20, status: str = None):
    """Get paginated list of quests"""
    try:
        params = f"?page={page}&page_size={page_size}"
        if status:
            params += f"&status={status}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/quests/paginated{params}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/scaling/stats")
async def proxy_scaling_stats():
    """Get performance and scaling statistics"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/scaling/stats")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/scaling/optimize")
async def proxy_scaling_optimize():
    """Trigger optimization tasks"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{get_npc_base_url()}/scaling/optimize")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/scaling/cache")
async def proxy_cache_stats():
    """Get cache statistics"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/scaling/cache")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/bulk/npc-data")
async def proxy_bulk_npc_data(npc_ids: str):
    """Get data for multiple NPCs in single request"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/bulk/npc-data?npc_ids={npc_ids}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/zone/{zone_id}/tick")
async def proxy_zone_tick(zone_id: str):
    """Process a tick for NPCs in a specific zone"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/zone/{zone_id}/tick")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/zone/{zone_id}/register")
async def proxy_zone_register(zone_id: str, npc_id: str):
    """Register an NPC to a zone"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/zone/{zone_id}/register?npc_id={npc_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# Voice System Proxy Endpoints
# ============================================================================

@api_router.get("/voice/available")
async def proxy_voice_available():
    """Get all available voice profiles"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/voice/available")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/voice/assignments")
async def proxy_voice_assignments():
    """Get current NPC voice assignments"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/voice/assignments")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/voice/assign/{npc_id}")
async def proxy_voice_assign(npc_id: str, voice_key: str = None):
    """Assign a voice to an NPC"""
    try:
        params = f"?voice_key={voice_key}" if voice_key else ""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/voice/assign/{npc_id}{params}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/voice/generate/{npc_id}")
async def proxy_voice_generate(npc_id: str, request: dict):
    """Generate speech audio for an NPC with unique fingerprint"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{get_npc_base_url()}/voice/generate/{npc_id}", json=request)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/voice/info/{npc_id}")
async def proxy_voice_info(npc_id: str):
    """Get detailed voice info for an NPC"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/voice/info/{npc_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/voice/clone/{npc_id}")
async def proxy_voice_clone(npc_id: str, request: dict):
    """Clone a custom voice for an NPC"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{get_npc_base_url()}/voice/clone/{npc_id}", json=request)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.delete("/voice/clone/{npc_id}")
async def proxy_voice_clone_delete(npc_id: str):
    """Delete a cloned voice"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(f"{get_npc_base_url()}/voice/clone/{npc_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/voice/preview")
async def proxy_voice_preview(request: dict):
    """Preview voice fingerprint for given personality"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/voice/preview", json=request)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/voice/stats")
async def proxy_voice_stats():
    """Get voice system statistics"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/voice/stats")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/voice/reset/{npc_id}")
async def proxy_voice_reset(npc_id: str):
    """Reset voice assignment for a specific NPC"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/voice/reset/{npc_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/voice/reset-all")
async def proxy_voice_reset_all():
    """Reset all voice assignments"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{get_npc_base_url()}/voice/reset-all")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# Speech-to-Text (STT) Proxy Endpoints
# ============================================================================

@api_router.post("/speech/transcribe")
async def proxy_speech_transcribe(request: Request):
    """Transcribe player speech to text using Whisper"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{get_npc_base_url()}/speech/transcribe", json=body)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/speech/interact/{npc_id}")
async def proxy_speech_interact(npc_id: str, request: Request, player_id: str = "default_player", player_name: str = "Traveler"):
    """Complete voice interaction: STT -> NPC Response -> TTS"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/speech/interact/{npc_id}?player_id={player_id}&player_name={player_name}",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# Multi-NPC Conversation Groups Proxy
# ============================================================================

@api_router.post("/conversation/location/npc/{npc_id}")
async def proxy_conversation_npc_location(npc_id: str, request: Request):
    """Update NPC location from Unreal Engine"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/location/npc/{npc_id}",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/location/player/{player_id}")
async def proxy_conversation_player_location(player_id: str, request: Request):
    """Update player location from Unreal Engine"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/location/player/{player_id}",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/location/batch")
async def proxy_conversation_batch_location(request: Request):
    """Batch update multiple locations"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/location/batch",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/conversation/nearby/{player_id}")
async def proxy_conversation_nearby(player_id: str, max_distance: float = None):
    """Get NPCs near the player"""
    try:
        url = f"{get_npc_base_url()}/conversation/nearby/{player_id}"
        if max_distance:
            url += f"?max_distance={max_distance}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/start")
async def proxy_conversation_start(request: Request):
    """Start a group conversation"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/start",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/{group_id}/message")
async def proxy_conversation_message(group_id: str, request: Request):
    """Send a message in a group conversation"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/{group_id}/message",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/{group_id}/add-npc")
async def proxy_conversation_add_npc(group_id: str, request: Request):
    """Add an NPC to a conversation"""
    try:
        body = await request.json()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/{group_id}/add-npc",
                json=body
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/{group_id}/remove-npc/{npc_id}")
async def proxy_conversation_remove_npc(group_id: str, npc_id: str):
    """Remove an NPC from a conversation"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/{group_id}/remove-npc/{npc_id}"
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/{group_id}/end")
async def proxy_conversation_end(group_id: str):
    """End a group conversation"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/{group_id}/end"
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/conversation/stats")
async def proxy_conversation_stats():
    """Get conversation system statistics"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{get_npc_base_url()}/conversation/stats"
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.post("/conversation/cleanup")
async def proxy_conversation_cleanup():
    """Cleanup expired conversations"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{get_npc_base_url()}/conversation/cleanup"
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/conversation/player/{player_id}/active")
async def proxy_conversation_player_active(player_id: str):
    """Get player's active conversations"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{get_npc_base_url()}/conversation/player/{player_id}/active"
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@api_router.get("/conversation/{group_id}")
async def proxy_conversation_get(group_id: str):
    """Get conversation state"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{get_npc_base_url()}/conversation/{group_id}"
            )
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# WebSocket Endpoint for Real-Time Game Communication
# ============================================================================

@app.websocket("/api/ws/game")
async def websocket_proxy(websocket: WebSocket, player_id: str = "default_player", player_name: str = "Traveler"):
    """
    WebSocket proxy to NPC service for real-time game communication.
    
    Connect: ws://{host}/api/ws/game?player_id=xxx&player_name=PlayerName
    
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
    """
    await websocket.accept()
    
    # Build the internal WebSocket URL
    ws_url = f"ws://localhost:8001/npc-direct/ws/game?player_id={player_id}&player_name={player_name}"
    
    try:
        async with websockets.connect(ws_url) as npc_ws:
            async def forward_to_client():
                """Forward messages from NPC service to client"""
                try:
                    async for message in npc_ws:
                        await websocket.send_text(message)
                except Exception as e:
                    logging.error(f"Error forwarding to client: {e}")
            
            async def forward_to_npc():
                """Forward messages from client to NPC service"""
                try:
                    while True:
                        data = await websocket.receive_text()
                        await npc_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logging.error(f"Error forwarding to NPC: {e}")
            
            # Run both tasks concurrently
            import asyncio
            done, pending = await asyncio.wait(
                [asyncio.create_task(forward_to_client()), asyncio.create_task(forward_to_npc())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                
    except Exception as e:
        logging.error(f"WebSocket proxy error: {e}")
        await websocket.close(code=1011, reason=str(e))

@api_router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status from NPC service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{get_npc_base_url()}/ws/status")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ============================================================================
# Authentication Endpoints (Direct MongoDB - for deployment)
# ============================================================================

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    player_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdatePlayerNameRequest(BaseModel):
    player_name: str

class UnrealAuthRequest(BaseModel):
    unreal_player_id: str
    player_name: Optional[str] = None
    password: Optional[str] = None

class GenerateAPIKeyRequest(BaseModel):
    description: Optional[str] = None
    expires_days: Optional[int] = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    if not credentials:
        return None
    result = auth_system.verify_token(credentials.credentials)
    if not result.get("valid"):
        return None
    return result

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require authentication"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = auth_system.verify_token(credentials.credentials)
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail=result.get("error", "Invalid token"))
    return result

@api_router.post("/auth/register")
async def auth_register(request: RegisterRequest):
    """Register a new user account"""
    result = await auth_system.register(
        username=request.username,
        password=request.password,
        email=request.email,
        player_name=request.player_name,
        auth_source="web"
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_router.post("/auth/login")
async def auth_login(request: LoginRequest):
    """Login with username/email and password"""
    result = await auth_system.login(request.username, request.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(require_auth)):
    """Get current user info"""
    full_user = await auth_system.get_user(user["user_id"])
    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")
    return full_user

@api_router.post("/auth/verify")
async def auth_verify(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify if a token is valid"""
    if not credentials:
        return {"valid": False, "error": "No token provided"}
    return auth_system.verify_token(credentials.credentials)

@api_router.put("/auth/player-name")
async def auth_update_player_name(request: UpdatePlayerNameRequest, user: dict = Depends(require_auth)):
    """Update player display name"""
    success = await auth_system.update_player_name(user["user_id"], request.player_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update player name")
    return {"success": True, "player_name": request.player_name}

@api_router.put("/auth/password")
async def auth_change_password(request: ChangePasswordRequest, user: dict = Depends(require_auth)):
    """Change password"""
    result = await auth_system.change_password(user["user_id"], request.old_password, request.new_password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_router.post("/auth/unreal/connect")
async def auth_unreal_connect(request: UnrealAuthRequest):
    """Unreal Engine player connection"""
    result = await auth_system.create_or_get_unreal_user(
        unreal_player_id=request.unreal_player_id,
        player_name=request.player_name,
        password=request.password
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_router.post("/auth/unreal/login")
async def auth_unreal_login(request: UnrealAuthRequest):
    """Unreal Engine player login"""
    if not request.password:
        raise HTTPException(status_code=400, detail="Password required")
    result = await auth_system.login(request.unreal_player_id, request.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@api_router.post("/auth/api-key")
async def auth_create_api_key(request: GenerateAPIKeyRequest, user: dict = Depends(require_auth)):
    """Generate API key"""
    result = await auth_system.generate_api_key(user["user_id"], request.description, request.expires_days)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_router.get("/auth/api-key/validate")
async def auth_validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Validate API key"""
    result = await auth_system.validate_api_key(x_api_key)
    if not result["valid"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@api_router.get("/auth/users")
async def auth_list_users(limit: int = 100, offset: int = 0, user: dict = Depends(require_auth)):
    """List all users"""
    return await auth_system.list_users(limit, offset)

async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

# Include NPC bridge router (optional - may not be available in all deployments)
try:
    from npc_bridge import npc_router
    app.include_router(npc_router, prefix="/api")
    NPC_BRIDGE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"NPC bridge not available: {e}. NPC features will use proxy mode.")
    NPC_BRIDGE_AVAILABLE = False

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize auth system indexes on startup"""
    try:
        await auth_system.initialize()
        logger.info("Auth system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize auth system: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
