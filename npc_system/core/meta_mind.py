"""Meta-Mind - Executive Function & Conflict Resolution"""
from typing import Dict
from datetime import datetime

class MetaMind:
    """Executive function that consolidates subsystems and resolves conflicts"""
    
    def __init__(self, npc_id: str, personality: Dict):
        self.npc_id = npc_id
        self.personality = personality
    
    def apply_trait_drift(self, trait_name: str, event_impact: float, memory_vault) -> float:
        """Apply personality drift based on experience (Trait Ledger)"""
        current_value = self.personality.get(trait_name, 0.5)
        
        # Calculate drift with inertia (trait resists change)
        inertia = 0.95  # High inertia = slow change
        drift = event_impact * (1 - inertia) * 0.1  # Small incremental change
        
        new_value = current_value + drift
        
        # Update personality
        self.personality[trait_name] = new_value
        
        # Log to trait ledger (async via memory vault)
        from database.memory_vault import TraitChange
        trait_change = TraitChange(
            trait_id=trait_name,
            npc_id=self.npc_id,
            delta=drift,
            reason=f"Event impact: {event_impact:+.2f}",
            timestamp=datetime.now().isoformat(),
            current_value=new_value
        )
        
        # For now, synchronous (will be async in full implementation)
        memory_vault._write_trait_sync(trait_change)
        
        return new_value
    
    def resolve_intent_conflicts(self, cognitive_frame: Dict, limbic_state: Dict) -> Dict:
        """Meta-Mind resolves conflicts between cognitive intent and vital needs"""
        intent = cognitive_frame.get("intent", "Guard")
        urgency = cognitive_frame.get("urgency", 0.5)
        
        # Vitals override
        hunger = limbic_state["vitals"]["hunger"]
        fatigue = limbic_state["vitals"]["fatigue"]
        
        # Critical hunger overrides most actions
        if hunger > 0.8 and intent not in ["Flee", "Assist"]:
            cognitive_frame["intent"] = "Investigate"  # Search for food
            cognitive_frame["internal_reflection"] += " [Meta: Hunger override - must find food]"
            cognitive_frame["urgency"] = max(urgency, 0.9)
        
        # Critical fatigue forces rest
        if fatigue > 0.9 and intent not in ["Flee"]:
            cognitive_frame["intent"] = "Ignore"  # Must rest
            cognitive_frame["dialogue"] = "I... need to rest..."
            cognitive_frame["urgency"] = 1.0
        
        return cognitive_frame
    
    def evaluate_trust_change(self, cognitive_frame: Dict, player_action: str) -> float:
        """Calculate trust modification based on action and personality"""
        trust_mod = cognitive_frame.get("trust_mod", 0.0)
        
        # Paranoid NPCs distrust more easily
        paranoia = self.personality.get("paranoia", 0.5)
        if paranoia > 0.7:
            trust_mod *= 1.5  # Amplify negative trust changes
        
        # Empathic NPCs trust more easily
        empathy = self.personality.get("empathy", 0.5)
        if empathy > 0.7 and trust_mod > 0:
            trust_mod *= 1.3  # Amplify positive trust changes
        
        return max(-0.1, min(0.1, trust_mod))  # Clamp to range
