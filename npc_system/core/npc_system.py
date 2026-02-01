"""Complete NPC System - Orchestrates all subsystems"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict
import json

from core.brain import CognitiveBrain
from core.limbic import LimbicSystem
from core.meta_mind import MetaMind
from database.memory_vault import MemoryVault, Memory


class NPCSystem:
    """Complete NPC with all cognitive subsystems"""
    
    def __init__(self, persona_path: str):
        # Load persona
        with open(persona_path, 'r') as f:
            self.persona = json.load(f)
        
        self.npc_id = self.persona["npc_id"]
        self.personality = self.persona["personality"]
        
        # Initialize subsystems
        self.memory_vault = MemoryVault()
        self.limbic = LimbicSystem(self.npc_id)
        self.brain = CognitiveBrain(
            self.npc_id,
            self.personality,
            self.memory_vault,
            self.limbic
        )
        self.meta_mind = MetaMind(self.npc_id, self.personality)
        
        # Load initial memories
        self._load_initial_memories()
        
        # Start autonomous loop (Thread B)
        self.autonomous_task = None
        
        print(f"\n{'='*60}")
        print(f"✓ NPC System Initialized: {self.npc_id}")
        print(f"  Role: {self.persona['role']}")
        print(f"  Location: {self.persona['location']}")
        print(f"{'='*60}\n")
    
    def _load_initial_memories(self):
        """Load initial memories from persona"""
        for mem_data in self.persona.get("initial_memories", []):
            memory = Memory(
                id=mem_data["id"],
                npc_id=self.npc_id,
                memory_type=mem_data["memory_type"],
                content=mem_data["content"],
                strength=mem_data["strength"],
                timestamp=datetime.now().isoformat()
            )
            self.memory_vault.save_memory(memory)
        print(f"✓ Loaded {len(self.persona.get('initial_memories', []))} initial memories")
    
    async def start_autonomous_systems(self):
        """Start Thread B: Autonomous vitals & reflection"""
        async def reflection_callback():
            await self.brain.autonomous_reflection()
        
        self.autonomous_task = asyncio.create_task(
            self.limbic.autonomous_loop(reflection_callback)
        )
        print("✓ Autonomous systems started (Thread B)")
    
    async def process_player_action(self, action: str) -> Dict:
        """Main cognitive loop - Thread A: Reactive"""
        print(f"\n[Player Action] {action}")
        print(f"[Think Time] {self.limbic.get_think_time():.1f}s")
        
        # Step 1: Cognitive processing (Brain)
        cognitive_frame = await self.brain.process_perception(action)
        
        # Step 2: Get limbic state
        limbic_state = self.limbic.get_state_summary()
        
        # Step 3: Meta-Mind conflict resolution
        resolved_frame = self.meta_mind.resolve_intent_conflicts(
            cognitive_frame,
            limbic_state
        )
        
        # Step 4: Update emotional state based on action
        if "threat" in action.lower() or "weapon" in action.lower():
            self.limbic.emotional_state.update_from_event("threat", 0.3)
        elif "help" in action.lower() or "assist" in action.lower():
            self.limbic.emotional_state.update_from_event("positive", 0.2)
        
        # Step 5: Save memory
        memory = Memory(
            id=f"mem_{uuid.uuid4().hex[:8]}",
            npc_id=self.npc_id,
            memory_type="episodic",
            content=f"Player action: {action}",
            strength=0.6,
            timestamp=datetime.now().isoformat()
        )
        self.memory_vault.save_memory(memory)
        
        # Step 6: Trait drift (if significant event)
        if resolved_frame.get("urgency", 0) > 0.7:
            if "threat" in action.lower():
                self.meta_mind.apply_trait_drift("paranoia", 0.1, self.memory_vault)
            elif "help" in action.lower():
                self.meta_mind.apply_trait_drift("empathy", 0.05, self.memory_vault)
        
        return {
            "cognitive_frame": resolved_frame,
            "limbic_state": limbic_state,
            "personality_snapshot": self.personality.copy()
        }
    
    def stop(self):
        """Stop all systems"""
        self.limbic.stop()
        if self.autonomous_task:
            self.autonomous_task.cancel()
        print("\n✓ NPC systems stopped")
    
    def display_response(self, response: Dict):
        """Pretty print NPC response"""
        cf = response["cognitive_frame"]
        ls = response["limbic_state"]
        
        print(f"\n{'─'*60}")
        print(f"🧠 INTERNAL THOUGHT (Hidden from Player):")
        print(f"   {cf['internal_reflection']}")
        print(f"\n💬 {self.npc_id} SAYS:")
        if cf['dialogue']:
            print(f"   \"{cf['dialogue']}\"")
        else:
            print(f"   [Remains silent]")
        print(f"\n📊 STATE:")
        print(f"   Intent: {cf['intent']} | Urgency: {cf['urgency']:.1f}")
        print(f"   Mood: {cf['emotional_state']} | Arousal: {ls['emotional_state']['arousal']:.1f}")
        print(f"   Hunger: {ls['vitals']['hunger']:.1f} | Fatigue: {ls['vitals']['fatigue']:.1f}")
        print(f"{'─'*60}\n")
