"""
Fractured Survival - WebSocket Handler for Real-Time Game Communication
Supports: NPC interaction, voice streaming, world events, faction updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional, Any
import asyncio
import json
import base64
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    # Client -> Server
    CONNECT = "connect"
    NPC_INIT = "npc_init"
    NPC_ACTION = "npc_action"
    NPC_STATUS = "npc_status"
    VOICE_GENERATE = "voice_generate"
    SPEECH_TRANSCRIBE = "speech_transcribe"
    SUBSCRIBE_EVENTS = "subscribe_events"
    UNSUBSCRIBE_EVENTS = "unsubscribe_events"
    GET_FACTIONS = "get_factions"
    GET_WORLD_EVENTS = "get_world_events"
    PING = "ping"
    
    # Conversation Groups (Client -> Server)
    UPDATE_LOCATION = "update_location"
    GET_NEARBY_NPCS = "get_nearby_npcs"
    START_CONVERSATION = "start_conversation"
    CONVERSATION_MESSAGE = "conversation_message"
    ADD_NPC_TO_CONVERSATION = "add_npc_to_conversation"
    REMOVE_NPC_FROM_CONVERSATION = "remove_npc_from_conversation"
    END_CONVERSATION = "end_conversation"
    GET_CONVERSATION = "get_conversation"
    
    # Server -> Client
    CONNECTED = "connected"
    NPC_INITIALIZED = "npc_initialized"
    NPC_RESPONSE = "npc_response"
    NPC_STATUS_RESPONSE = "npc_status_response"
    VOICE_CHUNK = "voice_chunk"
    VOICE_COMPLETE = "voice_complete"
    TRANSCRIPTION = "transcription"
    WORLD_EVENT = "world_event"
    FACTION_UPDATE = "faction_update"
    TERRITORY_UPDATE = "territory_update"
    QUEST_UPDATE = "quest_update"
    ERROR = "error"
    PONG = "pong"
    
    # Conversation Groups (Server -> Client)
    LOCATION_UPDATED = "location_updated"
    NEARBY_NPCS = "nearby_npcs"
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_RESPONSES = "conversation_responses"
    CONVERSATION_NPC_ADDED = "conversation_npc_added"
    CONVERSATION_NPC_REMOVED = "conversation_npc_removed"
    CONVERSATION_ENDED = "conversation_ended"
    CONVERSATION_STATE = "conversation_state"


@dataclass
class GameClient:
    """Represents a connected game client"""
    websocket: WebSocket
    player_id: str
    player_name: str = "Unknown"
    connected_at: float = field(default_factory=time.time)
    subscriptions: Set[str] = field(default_factory=set)
    last_ping: float = field(default_factory=time.time)


class WebSocketManager:
    """Manages WebSocket connections and message routing"""
    
    def __init__(self):
        self.active_connections: Dict[str, GameClient] = {}
        self.event_subscribers: Dict[str, Set[str]] = {
            "world_events": set(),
            "faction_updates": set(),
            "territory_updates": set(),
            "quest_updates": set(),
        }
        self._broadcast_lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, player_id: str, player_name: str = "Unknown") -> GameClient:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        client = GameClient(
            websocket=websocket,
            player_id=player_id,
            player_name=player_name
        )
        self.active_connections[player_id] = client
        logger.info(f"WebSocket connected: {player_id} ({player_name})")
        return client
    
    def disconnect(self, player_id: str):
        """Remove a WebSocket connection"""
        if player_id in self.active_connections:
            # Remove from all subscriptions
            for sub_set in self.event_subscribers.values():
                sub_set.discard(player_id)
            del self.active_connections[player_id]
            logger.info(f"WebSocket disconnected: {player_id}")
    
    async def send_message(self, player_id: str, message: dict):
        """Send a message to a specific client"""
        if player_id in self.active_connections:
            try:
                await self.active_connections[player_id].websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {player_id}: {e}")
                self.disconnect(player_id)
    
    async def send_error(self, player_id: str, error: str, request_id: str = None):
        """Send an error message to a client"""
        msg = {
            "type": MessageType.ERROR,
            "error": error,
            "timestamp": time.time()
        }
        if request_id:
            msg["request_id"] = request_id
        await self.send_message(player_id, msg)
    
    async def broadcast(self, event_type: str, message: dict):
        """Broadcast a message to all subscribers of an event type"""
        async with self._broadcast_lock:
            subscribers = self.event_subscribers.get(event_type, set()).copy()
            for player_id in subscribers:
                await self.send_message(player_id, message)
    
    def subscribe(self, player_id: str, event_type: str):
        """Subscribe a client to an event type"""
        if event_type in self.event_subscribers:
            self.event_subscribers[event_type].add(player_id)
            if player_id in self.active_connections:
                self.active_connections[player_id].subscriptions.add(event_type)
            logger.info(f"{player_id} subscribed to {event_type}")
    
    def unsubscribe(self, player_id: str, event_type: str):
        """Unsubscribe a client from an event type"""
        if event_type in self.event_subscribers:
            self.event_subscribers[event_type].discard(player_id)
            if player_id in self.active_connections:
                self.active_connections[player_id].subscriptions.discard(event_type)
            logger.info(f"{player_id} unsubscribed from {event_type}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def is_connected(self, player_id: str) -> bool:
        """Check if a player is connected"""
        return player_id in self.active_connections


# Global WebSocket manager instance
ws_manager = WebSocketManager()


class WebSocketHandler:
    """Handles WebSocket message processing"""
    
    def __init__(self, npc_instances: dict, npc_voice_system, stt_client, 
                 world_simulator, faction_system, territory_system, quest_generator,
                 conversation_manager=None):
        self.npc_instances = npc_instances
        self.voice_system = npc_voice_system
        self.stt_client = stt_client
        self.world_simulator = world_simulator
        self.faction_system = faction_system
        self.territory_system = territory_system
        self.quest_generator = quest_generator
        self.conversation_manager = conversation_manager
    
    def set_conversation_manager(self, conversation_manager):
        """Set conversation manager reference"""
        self.conversation_manager = conversation_manager
        if conversation_manager:
            conversation_manager.set_npc_instances(self.npc_instances)
    
    async def handle_message(self, client: GameClient, message: dict) -> Optional[dict]:
        """Route and handle incoming WebSocket messages"""
        msg_type = message.get("type", "").lower()
        request_id = message.get("request_id")
        
        handlers = {
            MessageType.PING: self._handle_ping,
            MessageType.NPC_INIT: self._handle_npc_init,
            MessageType.NPC_ACTION: self._handle_npc_action,
            MessageType.NPC_STATUS: self._handle_npc_status,
            MessageType.VOICE_GENERATE: self._handle_voice_generate,
            MessageType.SPEECH_TRANSCRIBE: self._handle_speech_transcribe,
            MessageType.SUBSCRIBE_EVENTS: self._handle_subscribe,
            MessageType.UNSUBSCRIBE_EVENTS: self._handle_unsubscribe,
            MessageType.GET_FACTIONS: self._handle_get_factions,
            MessageType.GET_WORLD_EVENTS: self._handle_get_world_events,
            # Conversation groups
            MessageType.UPDATE_LOCATION: self._handle_update_location,
            MessageType.GET_NEARBY_NPCS: self._handle_get_nearby_npcs,
            MessageType.START_CONVERSATION: self._handle_start_conversation,
            MessageType.CONVERSATION_MESSAGE: self._handle_conversation_message,
            MessageType.ADD_NPC_TO_CONVERSATION: self._handle_add_npc_to_conversation,
            MessageType.REMOVE_NPC_FROM_CONVERSATION: self._handle_remove_npc_from_conversation,
            MessageType.END_CONVERSATION: self._handle_end_conversation,
            MessageType.GET_CONVERSATION: self._handle_get_conversation,
        }
        
        handler = handlers.get(msg_type)
        if handler:
            try:
                response = await handler(client, message)
                if response and request_id:
                    response["request_id"] = request_id
                return response
            except Exception as e:
                logger.error(f"Error handling {msg_type}: {e}")
                return {
                    "type": MessageType.ERROR,
                    "error": str(e),
                    "request_id": request_id
                }
        else:
            return {
                "type": MessageType.ERROR,
                "error": f"Unknown message type: {msg_type}",
                "request_id": request_id
            }
    
    async def _handle_ping(self, client: GameClient, message: dict) -> dict:
        """Handle ping message"""
        client.last_ping = time.time()
        return {
            "type": MessageType.PONG,
            "timestamp": time.time()
        }
    
    async def _handle_npc_init(self, client: GameClient, message: dict) -> dict:
        """Handle NPC initialization"""
        npc_id = message.get("npc_id")
        if not npc_id:
            return {"type": MessageType.ERROR, "error": "npc_id required"}
        
        # Check if already initialized
        if npc_id in self.npc_instances:
            npc = self.npc_instances[npc_id]
            return {
                "type": MessageType.NPC_INITIALIZED,
                "status": "already_exists",
                "npc_id": npc_id,
                "role": npc.persona.get("role", "Unknown"),
                "location": npc.persona.get("location", "Unknown")
            }
        
        # Initialize NPC (this will be called from the main service)
        return {
            "type": MessageType.NPC_INITIALIZED,
            "status": "init_required",
            "npc_id": npc_id,
            "message": "Use HTTP /npc/init or wait for NPC manager"
        }
    
    async def _handle_npc_action(self, client: GameClient, message: dict) -> dict:
        """Handle NPC action/dialogue"""
        npc_id = message.get("npc_id")
        action = message.get("action")
        
        if not npc_id or not action:
            return {"type": MessageType.ERROR, "error": "npc_id and action required"}
        
        if npc_id not in self.npc_instances:
            return {"type": MessageType.ERROR, "error": f"NPC {npc_id} not initialized"}
        
        npc = self.npc_instances[npc_id]
        
        # Process the action through the NPC's cognitive system
        try:
            # Build context with player info
            context = f"Player {client.player_name} (ID: {client.player_id}) says: {action}"
            response = await npc.process_player_action(context)
            
            cognitive_frame = response.get("cognitive_frame", {})
            limbic_state = response.get("limbic_state", {})
            
            return {
                "type": MessageType.NPC_RESPONSE,
                "npc_id": npc_id,
                "player_id": client.player_id,
                "dialogue": cognitive_frame.get("dialogue", ""),
                "inner_thoughts": cognitive_frame.get("internal_reflection", ""),
                "mood_shift": cognitive_frame.get("mood_shift", "neutral"),
                "intent": cognitive_frame.get("intent", "none"),
                "emotional_state": cognitive_frame.get("emotional_state", "neutral"),
                "urgency": cognitive_frame.get("urgency", 0.5),
                "limbic_state": limbic_state,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"NPC action error: {e}")
            return {"type": MessageType.ERROR, "error": f"NPC processing error: {str(e)}"}
    
    async def _handle_npc_status(self, client: GameClient, message: dict) -> dict:
        """Handle NPC status request"""
        npc_id = message.get("npc_id")
        
        if not npc_id:
            return {"type": MessageType.ERROR, "error": "npc_id required"}
        
        if npc_id not in self.npc_instances:
            return {"type": MessageType.ERROR, "error": f"NPC {npc_id} not initialized"}
        
        npc = self.npc_instances[npc_id]
        
        return {
            "type": MessageType.NPC_STATUS_RESPONSE,
            "npc_id": npc_id,
            "status": "active",
            "role": npc.persona.get("role", "Unknown"),
            "location": npc.persona.get("location", "Unknown"),
            "emotional_state": npc.emotional_state if hasattr(npc, 'emotional_state') else {},
            "timestamp": time.time()
        }
    
    async def _handle_voice_generate(self, client: GameClient, message: dict) -> None:
        """Handle voice generation with streaming"""
        npc_id = message.get("npc_id")
        text = message.get("text")
        mood = message.get("mood", "neutral")
        audio_format = message.get("format", "wav")
        request_id = message.get("request_id")
        
        if not npc_id or not text:
            await ws_manager.send_error(client.player_id, "npc_id and text required", request_id)
            return
        
        if npc_id not in self.npc_instances:
            await ws_manager.send_error(client.player_id, f"NPC {npc_id} not initialized", request_id)
            return
        
        npc = self.npc_instances[npc_id]
        persona = npc.persona if hasattr(npc, 'persona') else {}
        
        if isinstance(persona, dict):
            role = persona.get('role', 'citizen')
            personality = persona.get('personality', {})
        else:
            role = getattr(persona, 'role', 'citizen')
            personality = getattr(persona, 'personality', {})
        
        if hasattr(personality, '__dict__'):
            personality = vars(personality)
        
        try:
            # Generate audio
            audio_bytes = await self.voice_system.generate_speech_async(
                npc_id=npc_id,
                text=text,
                mood=mood,
                role=role,
                personality=personality
            )
            
            if not audio_bytes:
                await ws_manager.send_error(client.player_id, "Voice generation failed", request_id)
                return
            
            # Convert to WAV if requested
            if audio_format.lower() == "wav":
                try:
                    import io
                    from pydub import AudioSegment
                    mp3_audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                    wav_buffer = io.BytesIO()
                    mp3_audio.export(wav_buffer, format="wav")
                    audio_bytes = wav_buffer.getvalue()
                except Exception as e:
                    logger.warning(f"WAV conversion failed, using MP3: {e}")
                    audio_format = "mp3"
            
            # Stream audio in chunks (16KB chunks for smooth streaming)
            chunk_size = 16384
            total_chunks = (len(audio_bytes) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                
                await ws_manager.send_message(client.player_id, {
                    "type": MessageType.VOICE_CHUNK,
                    "npc_id": npc_id,
                    "chunk_index": i // chunk_size,
                    "total_chunks": total_chunks,
                    "audio_data": chunk_b64,
                    "format": audio_format,
                    "request_id": request_id
                })
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Send completion message
            await ws_manager.send_message(client.player_id, {
                "type": MessageType.VOICE_COMPLETE,
                "npc_id": npc_id,
                "text": text,
                "format": audio_format,
                "total_size": len(audio_bytes),
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Voice generation error: {e}")
            await ws_manager.send_error(client.player_id, f"Voice error: {str(e)}", request_id)
    
    async def _handle_speech_transcribe(self, client: GameClient, message: dict) -> dict:
        """Handle speech-to-text transcription"""
        audio_base64 = message.get("audio_base64")
        language = message.get("language", "en")
        
        if not audio_base64:
            return {"type": MessageType.ERROR, "error": "audio_base64 required"}
        
        try:
            audio_bytes = base64.b64decode(audio_base64)
            transcription = await self.stt_client.transcribe(
                audio_bytes=audio_bytes,
                language=language
            )
            
            return {
                "type": MessageType.TRANSCRIPTION,
                "text": transcription,
                "language": language,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {"type": MessageType.ERROR, "error": f"Transcription failed: {str(e)}"}
    
    async def _handle_subscribe(self, client: GameClient, message: dict) -> dict:
        """Handle event subscription"""
        events = message.get("events", [])
        if isinstance(events, str):
            events = [events]
        
        subscribed = []
        for event in events:
            ws_manager.subscribe(client.player_id, event)
            subscribed.append(event)
        
        return {
            "type": "subscribed",
            "events": subscribed,
            "timestamp": time.time()
        }
    
    async def _handle_unsubscribe(self, client: GameClient, message: dict) -> dict:
        """Handle event unsubscription"""
        events = message.get("events", [])
        if isinstance(events, str):
            events = [events]
        
        unsubscribed = []
        for event in events:
            ws_manager.unsubscribe(client.player_id, event)
            unsubscribed.append(event)
        
        return {
            "type": "unsubscribed",
            "events": unsubscribed,
            "timestamp": time.time()
        }
    
    async def _handle_get_factions(self, client: GameClient, message: dict) -> dict:
        """Handle faction list request"""
        try:
            factions = self.faction_system.get_all_factions() if self.faction_system else []
            return {
                "type": "factions",
                "factions": factions,
                "timestamp": time.time()
            }
        except Exception as e:
            return {"type": MessageType.ERROR, "error": str(e)}
    
    async def _handle_get_world_events(self, client: GameClient, message: dict) -> dict:
        """Handle world events request"""
        limit = message.get("limit", 10)
        try:
            events = self.world_simulator.get_recent_events(limit) if self.world_simulator else []
            return {
                "type": "world_events",
                "events": events,
                "timestamp": time.time()
            }
        except Exception as e:
            return {"type": MessageType.ERROR, "error": str(e)}

    # ============================================================================
    # Conversation Group Handlers
    # ============================================================================
    
    async def _handle_update_location(self, client: GameClient, message: dict) -> dict:
        """
        Update NPC or player location from Unreal Engine.
        Message: { "type": "update_location", "entity_type": "npc"|"player", "entity_id": "...", 
                   "x": 0, "y": 0, "z": 0, "zone": "area_name" }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        entity_type = message.get("entity_type", "player")
        entity_id = message.get("entity_id", client.player_id)
        x = message.get("x", 0)
        y = message.get("y", 0)
        z = message.get("z", 0)
        zone = message.get("zone", "unknown")
        
        if entity_type == "npc":
            self.conversation_manager.update_npc_location(entity_id, x, y, z, zone)
        else:
            self.conversation_manager.update_player_location(entity_id, x, y, z, zone)
        
        return {
            "type": MessageType.LOCATION_UPDATED,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "location": {"x": x, "y": y, "z": z, "zone": zone},
            "timestamp": time.time()
        }
    
    async def _handle_get_nearby_npcs(self, client: GameClient, message: dict) -> dict:
        """
        Get NPCs near the player based on location data.
        Message: { "type": "get_nearby_npcs", "max_distance": 500 (optional) }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        max_distance = message.get("max_distance")
        nearby = self.conversation_manager.get_nearby_npcs(client.player_id, max_distance)
        
        # Get NPC details
        npc_details = []
        for npc_id in nearby:
            if npc_id in self.npc_instances:
                npc = self.npc_instances[npc_id]
                persona = npc.persona if hasattr(npc, 'persona') else {}
                name = persona.get("name", npc_id) if isinstance(persona, dict) else npc_id
                role = persona.get("role", "Unknown") if isinstance(persona, dict) else "Unknown"
                
                loc = self.conversation_manager.npc_locations.get(npc_id)
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
            "type": MessageType.NEARBY_NPCS,
            "player_id": client.player_id,
            "nearby_npcs": npc_details,
            "count": len(npc_details),
            "timestamp": time.time()
        }
    
    async def _handle_start_conversation(self, client: GameClient, message: dict) -> dict:
        """
        Start a multi-NPC group conversation.
        Message: { "type": "start_conversation", "npc_ids": ["npc1", "npc2"] (optional), 
                   "location": "area_name", "auto_discover": true }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        npc_ids = message.get("npc_ids")
        location = message.get("location", "unknown")
        auto_discover = message.get("auto_discover", True)
        
        try:
            group = await self.conversation_manager.start_group_conversation(
                player_id=client.player_id,
                player_name=client.player_name,
                npc_ids=npc_ids,
                location=location,
                auto_discover=auto_discover
            )
            
            # Get participant details
            participants = []
            for npc_id, participant in group.participants.items():
                if npc_id in self.npc_instances:
                    npc = self.npc_instances[npc_id]
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
                "type": MessageType.CONVERSATION_STARTED,
                "group_id": group.group_id,
                "location": group.location,
                "participants": participants,
                "timestamp": time.time()
            }
            
        except ValueError as e:
            return {"type": MessageType.ERROR, "error": str(e)}
        except Exception as e:
            logger.error(f"Start conversation error: {e}")
            return {"type": MessageType.ERROR, "error": str(e)}
    
    async def _handle_conversation_message(self, client: GameClient, message: dict) -> dict:
        """
        Send a message in a group conversation.
        Message: { "type": "conversation_message", "group_id": "...", "message": "...", 
                   "target_npc_id": "..." (optional), "with_voice": false, "voice_format": "wav" }
        
        If with_voice=True, voice audio will be streamed separately for each NPC.
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        group_id = message.get("group_id")
        text = message.get("message", "")
        target_npc_id = message.get("target_npc_id")
        with_voice = message.get("with_voice", False)
        voice_format = message.get("voice_format", "wav")
        
        if not group_id or not text:
            return {"type": MessageType.ERROR, "error": "group_id and message required"}
        
        try:
            # Import ResponseType for formatting
            from core.conversation_groups import ResponseType
            
            responses = await self.conversation_manager.process_player_message(
                group_id=group_id,
                message=text,
                target_npc_id=target_npc_id
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
            group = self.conversation_manager.get_conversation(group_id)
            
            result = {
                "type": MessageType.CONVERSATION_RESPONSES,
                "group_id": group_id,
                "responses": formatted_responses,
                "response_count": len(formatted_responses),
                "tension_level": group.tension_level if group else 0,
                "topic": group.topic if group else "general",
                "timestamp": time.time()
            }
            
            # Generate voice if requested - stream each NPC's voice AFTER text response
            if with_voice and responses:
                voice_results = await self.conversation_manager.generate_voice_for_responses(
                    responses, 
                    audio_format=voice_format
                )
                
                result["voice_count"] = len(voice_results)
                result["voice_format"] = voice_format
                
                # First send the text response
                await ws_manager.send_message(client.player_id, result)
                
                # Stream voice responses in chunks (16KB chunks for large audio)
                CHUNK_SIZE = 16 * 1024  # 16KB chunks
                
                for voice_idx, voice_resp in enumerate(voice_results):
                    audio_b64 = voice_resp.get("audio_base64", "")
                    
                    if audio_b64:
                        # Split audio into chunks
                        chunks = [audio_b64[i:i+CHUNK_SIZE] for i in range(0, len(audio_b64), CHUNK_SIZE)]
                        total_chunks = len(chunks)
                        
                        for chunk_idx, chunk in enumerate(chunks):
                            await ws_manager.send_message(client.player_id, {
                                "type": "conversation_voice_chunk",
                                "group_id": group_id,
                                "npc_id": voice_resp.get("npc_id"),
                                "npc_name": voice_resp.get("npc_name"),
                                "voice_index": voice_idx,
                                "chunk_index": chunk_idx,
                                "total_chunks": total_chunks,
                                "audio_chunk": chunk,
                                "format": voice_format,
                                "timestamp": time.time()
                            })
                        
                        # Send completion message for this NPC's voice
                        await ws_manager.send_message(client.player_id, {
                            "type": "conversation_voice_complete",
                            "group_id": group_id,
                            "npc_id": voice_resp.get("npc_id"),
                            "npc_name": voice_resp.get("npc_name"),
                            "voice_index": voice_idx,
                            "dialogue": voice_resp.get("dialogue"),
                            "response_type": voice_resp.get("response_type"),
                            "mood": voice_resp.get("mood"),
                            "format": voice_format,
                            "total_chunks": total_chunks,
                            "timestamp": time.time()
                        })
                    else:
                        # No audio - send error
                        await ws_manager.send_message(client.player_id, {
                            "type": "conversation_voice_error",
                            "group_id": group_id,
                            "npc_id": voice_resp.get("npc_id"),
                            "npc_name": voice_resp.get("npc_name"),
                            "error": voice_resp.get("error", "No audio generated"),
                            "timestamp": time.time()
                        })
                
                # Return None since we already sent the response
                return None
            
            return result
            
        except ValueError as e:
            return {"type": MessageType.ERROR, "error": str(e)}
        except Exception as e:
            logger.error(f"Conversation message error: {e}")
            return {"type": MessageType.ERROR, "error": str(e)}
    
    async def _handle_add_npc_to_conversation(self, client: GameClient, message: dict) -> dict:
        """
        Add an NPC to an existing conversation.
        Message: { "type": "add_npc_to_conversation", "group_id": "...", "npc_id": "..." }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        group_id = message.get("group_id")
        npc_id = message.get("npc_id")
        
        if not group_id or not npc_id:
            return {"type": MessageType.ERROR, "error": "group_id and npc_id required"}
        
        success = await self.conversation_manager.add_npc_to_conversation(group_id, npc_id)
        
        if not success:
            return {"type": MessageType.ERROR, "error": "Could not add NPC to conversation"}
        
        group = self.conversation_manager.get_conversation(group_id)
        
        return {
            "type": MessageType.CONVERSATION_NPC_ADDED,
            "group_id": group_id,
            "npc_id": npc_id,
            "total_participants": len(group.participants) if group else 0,
            "timestamp": time.time()
        }
    
    async def _handle_remove_npc_from_conversation(self, client: GameClient, message: dict) -> dict:
        """
        Remove an NPC from a conversation.
        Message: { "type": "remove_npc_from_conversation", "group_id": "...", "npc_id": "..." }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        group_id = message.get("group_id")
        npc_id = message.get("npc_id")
        
        if not group_id or not npc_id:
            return {"type": MessageType.ERROR, "error": "group_id and npc_id required"}
        
        success = await self.conversation_manager.remove_npc_from_conversation(group_id, npc_id)
        
        if not success:
            return {"type": MessageType.ERROR, "error": "Could not remove NPC from conversation"}
        
        return {
            "type": MessageType.CONVERSATION_NPC_REMOVED,
            "group_id": group_id,
            "npc_id": npc_id,
            "timestamp": time.time()
        }
    
    async def _handle_end_conversation(self, client: GameClient, message: dict) -> dict:
        """
        End a group conversation.
        Message: { "type": "end_conversation", "group_id": "..." }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        group_id = message.get("group_id")
        
        if not group_id:
            return {"type": MessageType.ERROR, "error": "group_id required"}
        
        group = self.conversation_manager.end_conversation(group_id)
        
        if not group:
            return {"type": MessageType.ERROR, "error": "Conversation not found"}
        
        return {
            "type": MessageType.CONVERSATION_ENDED,
            "group_id": group_id,
            "duration_seconds": time.time() - group.started_at,
            "total_messages": len(group.history),
            "final_tension": group.tension_level,
            "timestamp": time.time()
        }
    
    async def _handle_get_conversation(self, client: GameClient, message: dict) -> dict:
        """
        Get current state of a group conversation.
        Message: { "type": "get_conversation", "group_id": "..." }
        """
        if not self.conversation_manager:
            return {"type": MessageType.ERROR, "error": "Conversation manager not initialized"}
        
        group_id = message.get("group_id")
        
        if not group_id:
            return {"type": MessageType.ERROR, "error": "group_id required"}
        
        group = self.conversation_manager.get_conversation(group_id)
        
        if not group:
            return {"type": MessageType.ERROR, "error": "Conversation not found"}
        
        # Import ResponseType for formatting
        from core.conversation_groups import ResponseType
        
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
            "type": MessageType.CONVERSATION_STATE,
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
            "last_activity": group.last_activity,
            "timestamp": time.time()
        }


# Event broadcaster for pushing updates to clients
class EventBroadcaster:
    """Broadcasts game events to subscribed WebSocket clients"""
    
    @staticmethod
    async def broadcast_world_event(event: dict):
        """Broadcast a world event to subscribers"""
        await ws_manager.broadcast("world_events", {
            "type": MessageType.WORLD_EVENT,
            "event": event,
            "timestamp": time.time()
        })
    
    @staticmethod
    async def broadcast_faction_update(faction_id: str, update: dict):
        """Broadcast a faction update to subscribers"""
        await ws_manager.broadcast("faction_updates", {
            "type": MessageType.FACTION_UPDATE,
            "faction_id": faction_id,
            "update": update,
            "timestamp": time.time()
        })
    
    @staticmethod
    async def broadcast_territory_update(territory_id: str, update: dict):
        """Broadcast a territory update to subscribers"""
        await ws_manager.broadcast("territory_updates", {
            "type": MessageType.TERRITORY_UPDATE,
            "territory_id": territory_id,
            "update": update,
            "timestamp": time.time()
        })
    
    @staticmethod
    async def broadcast_quest_update(quest_id: str, update: dict):
        """Broadcast a quest update to subscribers"""
        await ws_manager.broadcast("quest_updates", {
            "type": MessageType.QUEST_UPDATE,
            "quest_id": quest_id,
            "update": update,
            "timestamp": time.time()
        })


event_broadcaster = EventBroadcaster()
