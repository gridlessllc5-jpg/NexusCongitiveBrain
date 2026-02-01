"""
Multi-NPC Conversation Groups System
Realistic group conversations with location-based grouping and AI-driven turn selection.
Integrates with Unreal Engine via WebSocket for real-time location updates.
"""
import asyncio
import json
import time
import uuid
import random
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv("/app/npc_system/.env")

# Use OpenAI-compatible adapter instead of emergentintegrations
try:
    from core.llm_adapter import LlmChat, UserMessage
except ImportError:
    from llm_adapter import LlmChat, UserMessage


class ConversationRole(str, Enum):
    """Role of a participant in the conversation"""
    SPEAKER = "speaker"           # Currently speaking
    LISTENER = "listener"         # Actively listening
    INTERJECTOR = "interjector"   # About to interrupt
    OBSERVER = "observer"         # Passively observing


class ResponseType(str, Enum):
    """Type of NPC response in group conversation"""
    DIRECT_REPLY = "direct_reply"       # Direct response to player
    AGREEMENT = "agreement"             # Agrees with another NPC
    DISAGREEMENT = "disagreement"       # Disagrees with another NPC
    ELABORATION = "elaboration"         # Adds to another NPC's point
    INTERRUPTION = "interruption"       # Interrupts the conversation
    REDIRECT = "redirect"               # Changes topic
    SILENT = "silent"                   # Chooses not to speak


@dataclass
class NPCLocation:
    """NPC location data from Unreal Engine"""
    npc_id: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    zone: str = "unknown"
    last_updated: float = field(default_factory=time.time)
    
    def distance_to(self, other: 'NPCLocation') -> float:
        """Calculate 3D distance to another location"""
        return ((self.x - other.x) ** 2 + 
                (self.y - other.y) ** 2 + 
                (self.z - other.z) ** 2) ** 0.5


@dataclass
class ConversationParticipant:
    """A participant in a group conversation"""
    npc_id: str
    role: ConversationRole = ConversationRole.LISTENER
    attention_level: float = 1.0  # 0-1, how engaged they are
    last_spoke_at: float = 0.0
    statements_count: int = 0
    mood: str = "neutral"
    relationship_to_player: float = 0.5  # -1 to 1


@dataclass
class ConversationMessage:
    """A message in the conversation history"""
    speaker_id: str  # NPC ID or "player"
    speaker_name: str
    content: str
    response_type: ResponseType
    target_id: Optional[str] = None  # Who they're responding to
    timestamp: float = field(default_factory=time.time)
    mood: str = "neutral"
    inner_thoughts: Optional[str] = None


@dataclass
class ConversationGroup:
    """A group conversation instance"""
    group_id: str
    player_id: str
    player_name: str
    participants: Dict[str, ConversationParticipant] = field(default_factory=dict)
    history: List[ConversationMessage] = field(default_factory=list)
    location: str = "unknown"
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_active: bool = True
    topic: str = "general"
    tension_level: float = 0.0  # 0-1, how heated the conversation is


class ConversationGroupManager:
    """
    Manages multi-NPC conversation groups with realistic dynamics.
    Uses Unreal Engine location data for automatic grouping.
    """
    
    # Distance threshold for NPCs to be considered "nearby" (in Unreal units)
    PROXIMITY_THRESHOLD = 500.0  # Adjustable based on game scale
    
    # Maximum NPCs in a conversation
    MAX_GROUP_SIZE = 6
    
    # Time before an inactive conversation expires (seconds)
    CONVERSATION_TIMEOUT = 300.0
    
    def __init__(self):
        self.active_groups: Dict[str, ConversationGroup] = {}
        self.npc_locations: Dict[str, NPCLocation] = {}
        self.npc_instances: Dict = {}  # Reference to actual NPC systems
        self.player_locations: Dict[str, NPCLocation] = {}  # Track player positions too
        
        # Initialize LLM for conversation orchestration
        # Supports both OPENAI_API_KEY and EMERGENT_LLM_KEY
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
        self._orchestrator_llm = LlmChat(
            api_key=api_key,
            session_id=f"conv_orchestrator_{time.time()}",
            system_message=self._build_orchestrator_prompt()
        ).with_model("openai", "gpt-4o")
        
        print("✓ Conversation Group Manager initialized")
    
    def _build_orchestrator_prompt(self) -> str:
        """System prompt for the conversation orchestrator"""
        return """You are a conversation orchestrator for a post-apocalyptic game.
Your job is to determine which NPC should speak next in a group conversation and how.

Given the conversation context, participants, and their personalities, decide:
1. Which NPC should respond (or if multiple should respond)
2. What type of response (agreement, disagreement, elaboration, interruption, etc.)
3. Whether the conversation tension should increase or decrease

Respond ONLY with valid JSON in this format:
{
    "next_speakers": [
        {
            "npc_id": "string",
            "response_type": "direct_reply|agreement|disagreement|elaboration|interruption|redirect|silent",
            "target_id": "string or null (who they're responding to)",
            "urgency": 0.0-1.0,
            "should_interrupt": false
        }
    ],
    "tension_change": -0.1 to 0.1,
    "reasoning": "brief explanation"
}

Consider:
- NPCs with high aggression are more likely to disagree or interrupt
- NPCs with high empathy are more likely to agree or elaborate
- NPCs with high paranoia may redirect to safety concerns
- Trust levels between NPCs affect their interactions
- Recent speakers should wait before speaking again (unless interrupting)
"""
    
    def set_npc_instances(self, instances: Dict):
        """Set reference to NPC system instances"""
        self.npc_instances = instances
    
    def update_npc_location(self, npc_id: str, x: float, y: float, z: float, zone: str = "unknown"):
        """Update NPC location from Unreal Engine"""
        self.npc_locations[npc_id] = NPCLocation(
            npc_id=npc_id,
            x=x, y=y, z=z,
            zone=zone,
            last_updated=time.time()
        )
    
    def update_player_location(self, player_id: str, x: float, y: float, z: float, zone: str = "unknown"):
        """Update player location from Unreal Engine"""
        self.player_locations[player_id] = NPCLocation(
            npc_id=player_id,
            x=x, y=y, z=z,
            zone=zone,
            last_updated=time.time()
        )
    
    def get_nearby_npcs(self, player_id: str, max_distance: float = None) -> List[str]:
        """Get NPCs near the player based on location data"""
        if player_id not in self.player_locations:
            # If no location data, return all active NPCs
            return list(self.npc_instances.keys())[:self.MAX_GROUP_SIZE]
        
        player_loc = self.player_locations[player_id]
        max_dist = max_distance or self.PROXIMITY_THRESHOLD
        
        nearby = []
        for npc_id, npc_loc in self.npc_locations.items():
            if npc_id in self.npc_instances:
                distance = player_loc.distance_to(npc_loc)
                if distance <= max_dist:
                    nearby.append((npc_id, distance))
        
        # Sort by distance and limit
        nearby.sort(key=lambda x: x[1])
        return [npc_id for npc_id, _ in nearby[:self.MAX_GROUP_SIZE]]
    
    def get_npcs_in_zone(self, zone: str) -> List[str]:
        """Get all NPCs in a specific zone"""
        return [
            npc_id for npc_id, loc in self.npc_locations.items()
            if loc.zone == zone and npc_id in self.npc_instances
        ]
    
    async def start_group_conversation(
        self,
        player_id: str,
        player_name: str,
        npc_ids: List[str] = None,
        location: str = "unknown",
        auto_discover: bool = True
    ) -> ConversationGroup:
        """
        Start a new group conversation.
        If npc_ids not provided and auto_discover=True, finds nearby NPCs.
        """
        # Determine participants
        if npc_ids:
            participants_ids = npc_ids[:self.MAX_GROUP_SIZE]
        elif auto_discover:
            participants_ids = self.get_nearby_npcs(player_id)
        else:
            participants_ids = []
        
        if not participants_ids:
            raise ValueError("No NPCs available for conversation")
        
        # Create conversation group
        group_id = f"conv_{uuid.uuid4().hex[:8]}"
        group = ConversationGroup(
            group_id=group_id,
            player_id=player_id,
            player_name=player_name,
            location=location
        )
        
        # Add participants
        for npc_id in participants_ids:
            if npc_id in self.npc_instances:
                npc = self.npc_instances[npc_id]
                persona = npc.persona if hasattr(npc, 'persona') else {}
                
                participant = ConversationParticipant(
                    npc_id=npc_id,
                    role=ConversationRole.LISTENER,
                    mood=npc.limbic.emotional_state.mood if hasattr(npc, 'limbic') else "neutral"
                )
                group.participants[npc_id] = participant
        
        self.active_groups[group_id] = group
        
        # Generate initial greeting context
        await self._generate_group_awareness(group)
        
        return group
    
    async def _generate_group_awareness(self, group: ConversationGroup):
        """Generate initial awareness of the group for each NPC"""
        participant_names = []
        for npc_id in group.participants:
            if npc_id in self.npc_instances:
                npc = self.npc_instances[npc_id]
                name = npc.persona.get("name", npc_id) if isinstance(npc.persona, dict) else npc_id
                participant_names.append(name)
        
        # Each NPC becomes aware of others present
        for npc_id, participant in group.participants.items():
            if npc_id in self.npc_instances:
                npc = self.npc_instances[npc_id]
                others = [n for n in participant_names if n != npc_id]
                if others:
                    awareness = f"You notice {', '.join(others)} are also present."
                    # Store this as a temporary context
                    participant.attention_level = 1.0
    
    async def process_player_message(
        self,
        group_id: str,
        message: str,
        target_npc_id: Optional[str] = None
    ) -> List[ConversationMessage]:
        """
        Process a player message in the group conversation.
        Returns responses from one or more NPCs.
        """
        if group_id not in self.active_groups:
            raise ValueError(f"Conversation group {group_id} not found")
        
        group = self.active_groups[group_id]
        group.last_activity = time.time()
        
        # Record player message
        player_msg = ConversationMessage(
            speaker_id="player",
            speaker_name=group.player_name,
            content=message,
            response_type=ResponseType.DIRECT_REPLY,
            target_id=target_npc_id
        )
        group.history.append(player_msg)
        
        # Determine which NPCs should respond and how
        responding_npcs = await self._determine_responders(group, message, target_npc_id)
        
        # Generate responses
        responses = []
        for responder_info in responding_npcs:
            npc_id = responder_info["npc_id"]
            response_type = ResponseType(responder_info["response_type"])
            target_id = responder_info.get("target_id")
            
            if response_type == ResponseType.SILENT:
                continue
            
            # Generate NPC response
            response = await self._generate_npc_response(
                group, npc_id, message, response_type, target_id
            )
            
            if response:
                responses.append(response)
                group.history.append(response)
                
                # Update participant state
                if npc_id in group.participants:
                    group.participants[npc_id].last_spoke_at = time.time()
                    group.participants[npc_id].statements_count += 1
        
        return responses
    
    async def _determine_responders(
        self,
        group: ConversationGroup,
        message: str,
        target_npc_id: Optional[str]
    ) -> List[Dict]:
        """Use AI to determine which NPCs should respond and how"""
        
        # If player directly addressed an NPC, they should respond first
        if target_npc_id and target_npc_id in group.participants:
            # But others might also chime in
            primary_responder = {
                "npc_id": target_npc_id,
                "response_type": "direct_reply",
                "target_id": "player",
                "urgency": 1.0,
                "should_interrupt": False
            }
            
            # Check if others might react
            secondary_responders = await self._get_secondary_responders(
                group, message, target_npc_id
            )
            
            return [primary_responder] + secondary_responders
        
        # Build context for orchestrator
        context = self._build_orchestrator_context(group, message)
        
        try:
            response = await self._orchestrator_llm.send_message(UserMessage(text=context))
            result = json.loads(response)
            
            # Update tension
            tension_change = result.get("tension_change", 0)
            group.tension_level = max(0, min(1, group.tension_level + tension_change))
            
            return result.get("next_speakers", [])
            
        except Exception as e:
            print(f"Orchestrator error: {e}")
            # Fallback: most relevant NPC responds
            return [self._get_default_responder(group)]
    
    async def _get_secondary_responders(
        self,
        group: ConversationGroup,
        message: str,
        primary_npc_id: str
    ) -> List[Dict]:
        """Determine if other NPCs should also respond"""
        secondary = []
        
        for npc_id, participant in group.participants.items():
            if npc_id == primary_npc_id:
                continue
            
            # Check if NPC would want to chime in
            if npc_id in self.npc_instances:
                npc = self.npc_instances[npc_id]
                personality = npc.personality if hasattr(npc, 'personality') else {}
                
                # High curiosity or empathy = more likely to comment
                curiosity = personality.get('curiosity', 0.5)
                empathy = personality.get('empathy', 0.5)
                aggression = personality.get('aggression', 0.5)
                
                # Calculate probability of chiming in
                chime_in_prob = (curiosity + empathy) / 4 + (aggression * 0.2)
                
                if random.random() < chime_in_prob:
                    # Determine type of response
                    if aggression > 0.6:
                        response_type = random.choice(["disagreement", "elaboration"])
                    elif empathy > 0.6:
                        response_type = random.choice(["agreement", "elaboration"])
                    else:
                        response_type = "elaboration"
                    
                    secondary.append({
                        "npc_id": npc_id,
                        "response_type": response_type,
                        "target_id": primary_npc_id,
                        "urgency": 0.5,
                        "should_interrupt": False
                    })
        
        return secondary[:2]  # Limit secondary responders
    
    def _build_orchestrator_context(self, group: ConversationGroup, message: str) -> str:
        """Build context string for the orchestrator LLM"""
        # Build participant info
        participants_info = []
        for npc_id, participant in group.participants.items():
            if npc_id in self.npc_instances:
                npc = self.npc_instances[npc_id]
                persona = npc.persona if hasattr(npc, 'persona') else {}
                personality = npc.personality if hasattr(npc, 'personality') else {}
                
                name = persona.get("name", npc_id) if isinstance(persona, dict) else npc_id
                role = persona.get("role", "unknown") if isinstance(persona, dict) else "unknown"
                
                participants_info.append({
                    "npc_id": npc_id,
                    "name": name,
                    "role": role,
                    "personality": personality,
                    "mood": participant.mood,
                    "last_spoke_seconds_ago": time.time() - participant.last_spoke_at if participant.last_spoke_at > 0 else 999,
                    "statements_count": participant.statements_count
                })
        
        # Build recent history
        recent_history = []
        for msg in group.history[-5:]:
            recent_history.append({
                "speaker": msg.speaker_name,
                "content": msg.content[:100],
                "type": msg.response_type.value if isinstance(msg.response_type, ResponseType) else msg.response_type
            })
        
        context = f"""CONVERSATION CONTEXT:
Location: {group.location}
Tension Level: {group.tension_level:.2f}
Topic: {group.topic}

PARTICIPANTS:
{json.dumps(participants_info, indent=2)}

RECENT HISTORY:
{json.dumps(recent_history, indent=2)}

PLAYER MESSAGE:
"{message}"

Determine which NPC(s) should respond and how."""
        
        return context
    
    def _get_default_responder(self, group: ConversationGroup) -> Dict:
        """Get a default responder when orchestrator fails"""
        # Pick the NPC who hasn't spoken in longest
        oldest_speaker = None
        oldest_time = float('inf')
        
        for npc_id, participant in group.participants.items():
            speak_time = participant.last_spoke_at or 0
            if speak_time < oldest_time:
                oldest_time = speak_time
                oldest_speaker = npc_id
        
        return {
            "npc_id": oldest_speaker or list(group.participants.keys())[0],
            "response_type": "direct_reply",
            "target_id": "player",
            "urgency": 0.7,
            "should_interrupt": False
        }
    
    async def _generate_npc_response(
        self,
        group: ConversationGroup,
        npc_id: str,
        player_message: str,
        response_type: ResponseType,
        target_id: Optional[str]
    ) -> Optional[ConversationMessage]:
        """Generate an NPC's response in the group conversation"""
        if npc_id not in self.npc_instances:
            return None
        
        npc = self.npc_instances[npc_id]
        
        # Build context for NPC's response
        context_parts = [
            f"[GROUP CONVERSATION at {group.location}]",
            f"Other participants: {', '.join([p for p in group.participants if p != npc_id])}",
            f"Tension level: {'high' if group.tension_level > 0.6 else 'moderate' if group.tension_level > 0.3 else 'calm'}"
        ]
        
        # Add recent history context
        if group.history:
            context_parts.append("\nRecent conversation:")
            for msg in group.history[-3:]:
                context_parts.append(f"  {msg.speaker_name}: {msg.content[:80]}...")
        
        # Add response type instruction
        response_instructions = {
            ResponseType.DIRECT_REPLY: "Respond directly to the player.",
            ResponseType.AGREEMENT: f"You agree with what {target_id} said. Express your agreement and maybe add your perspective.",
            ResponseType.DISAGREEMENT: f"You disagree with {target_id}. Voice your disagreement respectfully but firmly.",
            ResponseType.ELABORATION: f"Build upon what {target_id} said. Add more information or context.",
            ResponseType.INTERRUPTION: "You feel compelled to interrupt. Make your point urgently.",
            ResponseType.REDIRECT: "Change the topic to something you think is more important."
        }
        
        context_parts.append(f"\n{response_instructions.get(response_type, '')}")
        context_parts.append(f"\nPlayer ({group.player_name}) says: {player_message}")
        
        full_context = "\n".join(context_parts)
        
        try:
            # Process through NPC's cognitive system
            response = await npc.process_player_action(full_context)
            
            cognitive_frame = response.get("cognitive_frame", {})
            dialogue = cognitive_frame.get("dialogue", "")
            mood = cognitive_frame.get("emotional_state", "neutral")
            inner_thoughts = cognitive_frame.get("internal_reflection", "")
            
            if not dialogue:
                return None
            
            # Get NPC name
            persona = npc.persona if hasattr(npc, 'persona') else {}
            name = persona.get("name", npc_id) if isinstance(persona, dict) else npc_id
            
            return ConversationMessage(
                speaker_id=npc_id,
                speaker_name=name,
                content=dialogue,
                response_type=response_type,
                target_id=target_id,
                mood=mood,
                inner_thoughts=inner_thoughts
            )
            
        except Exception as e:
            print(f"Error generating NPC response: {e}")
            return None
    
    async def add_npc_to_conversation(self, group_id: str, npc_id: str) -> bool:
        """Add an NPC to an existing conversation"""
        if group_id not in self.active_groups:
            return False
        
        group = self.active_groups[group_id]
        
        if len(group.participants) >= self.MAX_GROUP_SIZE:
            return False
        
        if npc_id in group.participants:
            return False
        
        if npc_id not in self.npc_instances:
            return False
        
        npc = self.npc_instances[npc_id]
        participant = ConversationParticipant(
            npc_id=npc_id,
            role=ConversationRole.LISTENER,
            mood=npc.limbic.emotional_state.mood if hasattr(npc, 'limbic') else "neutral"
        )
        group.participants[npc_id] = participant
        
        # Notify existing participants
        arrival_msg = ConversationMessage(
            speaker_id="system",
            speaker_name="System",
            content=f"{npc_id} has joined the conversation.",
            response_type=ResponseType.SILENT
        )
        group.history.append(arrival_msg)
        
        return True
    
    async def remove_npc_from_conversation(self, group_id: str, npc_id: str) -> bool:
        """Remove an NPC from a conversation"""
        if group_id not in self.active_groups:
            return False
        
        group = self.active_groups[group_id]
        
        if npc_id not in group.participants:
            return False
        
        del group.participants[npc_id]
        
        # If no participants left, end the conversation
        if not group.participants:
            group.is_active = False
        
        return True
    
    def end_conversation(self, group_id: str) -> Optional[ConversationGroup]:
        """End a conversation and return its final state"""
        if group_id not in self.active_groups:
            return None
        
        group = self.active_groups[group_id]
        group.is_active = False
        
        return group
    
    def get_conversation(self, group_id: str) -> Optional[ConversationGroup]:
        """Get a conversation by ID"""
        return self.active_groups.get(group_id)
    
    def get_player_conversations(self, player_id: str) -> List[ConversationGroup]:
        """Get all active conversations for a player"""
        return [
            group for group in self.active_groups.values()
            if group.player_id == player_id and group.is_active
        ]
    
    def cleanup_expired_conversations(self) -> int:
        """Remove expired conversations"""
        now = time.time()
        expired = []
        
        for group_id, group in self.active_groups.items():
            if now - group.last_activity > self.CONVERSATION_TIMEOUT:
                expired.append(group_id)
        
        for group_id in expired:
            self.active_groups[group_id].is_active = False
        
        return len(expired)
    
    def get_stats(self) -> Dict:
        """Get conversation system statistics"""
        active_count = sum(1 for g in self.active_groups.values() if g.is_active)
        return {
            "total_conversations": len(self.active_groups),
            "active_conversations": active_count,
            "tracked_npc_locations": len(self.npc_locations),
            "tracked_player_locations": len(self.player_locations),
            "max_group_size": self.MAX_GROUP_SIZE,
            "proximity_threshold": self.PROXIMITY_THRESHOLD
        }
    
    def set_voice_system(self, voice_system):
        """Set reference to voice system for TTS generation"""
        self.voice_system = voice_system
    
    async def generate_voice_for_responses(
        self,
        responses: List[ConversationMessage],
        audio_format: str = "wav"
    ) -> List[Dict]:
        """
        Generate voice audio for each NPC response in the conversation.
        Returns list of audio data with NPC metadata.
        """
        if not hasattr(self, 'voice_system') or not self.voice_system:
            return []
        
        voice_results = []
        
        for resp in responses:
            npc_id = resp.speaker_id
            if npc_id == "player" or npc_id == "system":
                continue
            
            try:
                # Get mood from response
                mood = resp.mood if resp.mood else "neutral"
                
                # Generate audio using voice system
                audio_result = await self.voice_system.generate_voice_async(
                    npc_id=npc_id,
                    text=resp.content,
                    mood=mood,
                    output_format=audio_format
                )
                
                if audio_result and audio_result.get("audio"):
                    voice_results.append({
                        "npc_id": npc_id,
                        "npc_name": resp.speaker_name,
                        "dialogue": resp.content,
                        "response_type": resp.response_type.value if isinstance(resp.response_type, ResponseType) else resp.response_type,
                        "audio_base64": audio_result.get("audio"),
                        "format": audio_format,
                        "duration_ms": audio_result.get("duration_ms", 0),
                        "voice_id": audio_result.get("voice_id", ""),
                        "mood": mood
                    })
            except Exception as e:
                print(f"Voice generation error for {npc_id}: {e}")
                # Include response without audio on error
                voice_results.append({
                    "npc_id": npc_id,
                    "npc_name": resp.speaker_name,
                    "dialogue": resp.content,
                    "response_type": resp.response_type.value if isinstance(resp.response_type, ResponseType) else resp.response_type,
                    "audio_base64": None,
                    "format": audio_format,
                    "error": str(e)
                })
        
        return voice_results


# Global conversation group manager instance
conversation_manager = ConversationGroupManager()
