"""Multi-NPC Orchestration System - Phase 3"""
import asyncio
from typing import Dict, List, Set
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NPCInteraction:
    """Record of interaction between NPCs"""
    from_npc: str
    to_npc: str
    action: str
    timestamp: str
    trust_impact: float = 0.0

class MultiNPCOrchestrator:
    """Manages interactions between multiple NPCs"""
    
    def __init__(self):
        self.npcs: Dict = {}  # npc_id -> NPCSystem instance
        self.trust_matrix: Dict[str, Dict[str, float]] = {}  # npc1 -> npc2 -> trust_value
        self.interaction_history: List[NPCInteraction] = []
        self.factions: Dict[str, Set[str]] = {
            "guards": set(),
            "traders": set(),
            "citizens": set()
        }
    
    def register_npc(self, npc_id: str, npc_instance, faction: str = "citizens"):
        """Register an NPC in the orchestrator"""
        self.npcs[npc_id] = npc_instance
        self.factions[faction].add(npc_id)
        
        # Initialize trust with other NPCs
        if npc_id not in self.trust_matrix:
            self.trust_matrix[npc_id] = {}
        
        for other_npc in self.npcs.keys():
            if other_npc != npc_id:
                # Same faction = higher initial trust
                if self._same_faction(npc_id, other_npc):
                    initial_trust = 0.6
                else:
                    initial_trust = 0.3
                
                self.trust_matrix[npc_id][other_npc] = initial_trust
                
                # Reciprocal trust
                if other_npc not in self.trust_matrix:
                    self.trust_matrix[other_npc] = {}
                self.trust_matrix[other_npc][npc_id] = initial_trust
    
    def _same_faction(self, npc1: str, npc2: str) -> bool:
        """Check if two NPCs are in the same faction"""
        for faction_members in self.factions.values():
            if npc1 in faction_members and npc2 in faction_members:
                return True
        return False
    
    def get_trust(self, from_npc: str, to_npc: str) -> float:
        """Get trust level from one NPC to another"""
        return self.trust_matrix.get(from_npc, {}).get(to_npc, 0.5)
    
    def modify_trust(self, from_npc: str, to_npc: str, delta: float):
        """Modify trust between NPCs"""
        if from_npc in self.trust_matrix:
            current = self.trust_matrix[from_npc].get(to_npc, 0.5)
            new_trust = max(0.0, min(1.0, current + delta))
            self.trust_matrix[from_npc][to_npc] = new_trust
            
            # Record in memory vault if significant change
            if abs(delta) > 0.05:
                npc = self.npcs.get(from_npc)
                if npc:
                    from database.memory_vault import Memory
                    import uuid
                    memory = Memory(
                        id=f"trust_{uuid.uuid4().hex[:8]}",
                        npc_id=from_npc,
                        memory_type="social",
                        content=f"Trust towards {to_npc} changed by {delta:+.2f} to {new_trust:.2f}",
                        strength=0.7,
                        timestamp=datetime.now().isoformat()
                    )
                    npc.memory_vault.save_memory(memory)
    
    async def npc_to_npc_interaction(self, from_npc_id: str, to_npc_id: str, 
                                     action: str) -> Dict:
        """Handle interaction from one NPC to another"""
        from_npc = self.npcs.get(from_npc_id)
        to_npc = self.npcs.get(to_npc_id)
        
        if not from_npc or not to_npc:
            return {"error": "NPC not found"}
        
        # Get current trust level
        trust_level = self.get_trust(to_npc_id, from_npc_id)
        
        # Build context for receiving NPC
        context = {
            "interaction_type": "npc_to_npc",
            "from_npc": from_npc_id,
            "trust_level": trust_level,
            "action": action
        }
        
        # Process through receiving NPC's cognitive system
        perception = f"{from_npc_id} (trust: {trust_level:.2f}): {action}"
        response = await to_npc.process_player_action(perception)
        
        # Update trust based on response
        if "trust_mod" in response["cognitive_frame"]:
            trust_delta = response["cognitive_frame"]["trust_mod"]
            self.modify_trust(to_npc_id, from_npc_id, trust_delta)
        
        # Record interaction
        interaction = NPCInteraction(
            from_npc=from_npc_id,
            to_npc=to_npc_id,
            action=action,
            timestamp=datetime.now().isoformat(),
            trust_impact=response["cognitive_frame"].get("trust_mod", 0.0)
        )
        self.interaction_history.append(interaction)
        
        return {
            "from_npc": from_npc_id,
            "to_npc": to_npc_id,
            "response": response,
            "trust_level": self.get_trust(to_npc_id, from_npc_id)
        }
    
    def get_faction_status(self) -> Dict:
        """Get status of all factions"""
        status = {}
        for faction_name, members in self.factions.items():
            status[faction_name] = {
                "members": list(members),
                "count": len(members),
                "average_trust": self._calculate_faction_trust(members)
            }
        return status
    
    def _calculate_faction_trust(self, members: Set[str]) -> float:
        """Calculate average trust within a faction"""
        if len(members) < 2:
            return 1.0
        
        total_trust = 0.0
        count = 0
        
        for npc1 in members:
            for npc2 in members:
                if npc1 != npc2:
                    total_trust += self.get_trust(npc1, npc2)
                    count += 1
        
        return total_trust / count if count > 0 else 0.5

# Global orchestrator instance
orchestrator = MultiNPCOrchestrator()
