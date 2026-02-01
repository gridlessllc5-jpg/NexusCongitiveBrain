"""
Dynamic NPC Generator - Create NPCs on the fly
Supports random generation and custom personality definition
"""
import random
import uuid
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class NPCTemplate:
    """Base template for NPC generation"""
    role_type: str  # gatekeeper, guard, merchant, civilian, scholar, warrior
    location: str
    faction: str  # guards, traders, citizens, scholars, warriors
    dialogue_style: str

# Role Templates
ROLE_TEMPLATES = {
    "gatekeeper": {
        "roles": ["Guarded Gatekeeper", "Suspicious Watchman", "Vigilant Sentry"],
        "locations": ["Porto Cobre Gates", "North Watch", "East Checkpoint"],
        "dialogue_styles": ["Direct and cautious", "Questioning and skeptical", "Blunt and defensive"],
        "base_traits": {"paranoia": (0.6, 0.9), "discipline": (0.5, 0.8)}
    },
    "guard": {
        "roles": ["Disciplined Protector", "Veteran Soldier", "Elite Defender"],
        "locations": ["Inner Gates", "Barracks", "Patrol Route"],
        "dialogue_styles": ["Military formal", "Strict and commanding", "Professional and direct"],
        "base_traits": {"discipline": (0.7, 0.9), "aggression": (0.4, 0.7)}
    },
    "merchant": {
        "roles": ["Opportunistic Trader", "Shrewd Dealer", "Cunning Broker"],
        "locations": ["Market District", "Trading Post", "Black Market"],
        "dialogue_styles": ["Friendly but calculating", "Persuasive", "Business-focused"],
        "base_traits": {"opportunism": (0.7, 0.95), "curiosity": (0.6, 0.8)}
    },
    "civilian": {
        "roles": ["Cautious Survivor", "Weary Refugee", "Hopeful Settler"],
        "locations": ["Residential Area", "Refugee Camp", "Safe House"],
        "dialogue_styles": ["Nervous and careful", "Grateful but scared", "Hopeful"],
        "base_traits": {"anxiety": (0.6, 0.9), "empathy": (0.5, 0.8)}
    },
    "scholar": {
        "roles": ["Wise Researcher", "Curious Academic", "Knowledge Keeper"],
        "locations": ["Library", "Research Lab", "Archive"],
        "dialogue_styles": ["Analytical and thoughtful", "Inquisitive", "Educational"],
        "base_traits": {"curiosity": (0.8, 0.95), "discipline": (0.6, 0.8)}
    },
    "warrior": {
        "roles": ["Battle-Hardened Fighter", "Fierce Combatant", "Tactical Warrior"],
        "locations": ["Training Ground", "Front Lines", "War Room"],
        "dialogue_styles": ["Aggressive and confident", "Strategic", "Direct and forceful"],
        "base_traits": {"aggression": (0.7, 0.9), "risk_tolerance": (0.6, 0.8)}
    }
}

class NPCGenerator:
    """Generate NPCs with random or custom personalities"""
    
    def __init__(self):
        self.generated_npcs = {}
    
    def generate_random_npc(self, 
                           role_type: Optional[str] = None,
                           name: Optional[str] = None) -> Dict:
        """
        Generate a random NPC with unique personality
        
        Args:
            role_type: Type of NPC (gatekeeper, guard, merchant, etc.)
            name: Optional custom name, otherwise auto-generated
        """
        # Select role type
        if role_type is None:
            role_type = random.choice(list(ROLE_TEMPLATES.keys()))
        
        if role_type not in ROLE_TEMPLATES:
            role_type = "civilian"
        
        template = ROLE_TEMPLATES[role_type]
        
        # Generate name if not provided
        if name is None:
            name = self._generate_name()
        
        # Select from template options
        role = random.choice(template["roles"])
        location = random.choice(template["locations"])
        dialogue_style = random.choice(template["dialogue_styles"])
        
        # Generate personality traits
        personality = self._generate_personality(template.get("base_traits", {}))
        
        # Generate backstory
        backstory = self._generate_backstory(name, role, location)
        
        # Create NPC definition
        npc_def = {
            "npc_id": name,
            "role": role,
            "location": location,
            "personality": personality,
            "initial_mood": self._select_initial_mood(personality),
            "initial_vitals": {
                "hunger": random.uniform(0.1, 0.4),
                "fatigue": random.uniform(0.1, 0.4)
            },
            "backstory": backstory,
            "initial_memories": self._generate_initial_memories(name, role, location),
            "current_goal": self._select_goal(role_type),
            "dialogue_style": dialogue_style
        }
        
        self.generated_npcs[name] = npc_def
        return npc_def
    
    def create_custom_npc(self,
                         name: str,
                         role: str,
                         location: str,
                         personality: Dict[str, float],
                         backstory: str,
                         dialogue_style: str = "Natural and contextual",
                         faction: str = "citizens") -> Dict:
        """
        Create a custom NPC with user-defined personality
        
        Args:
            name: NPC name/ID
            role: NPC role description
            location: Where the NPC is stationed
            personality: Dict of trait values (0.0-1.0)
            backstory: NPC background story
            dialogue_style: How the NPC speaks
            faction: Which faction the NPC belongs to
        """
        # Validate personality traits
        valid_traits = ["curiosity", "empathy", "risk_tolerance", "aggression", 
                       "discipline", "romanticism", "opportunism", "paranoia"]
        
        # Ensure all traits exist, fill missing with defaults
        full_personality = {
            "curiosity": 0.5,
            "empathy": 0.5,
            "risk_tolerance": 0.5,
            "aggression": 0.5,
            "discipline": 0.5,
            "romanticism": 0.5,
            "opportunism": 0.5,
            "paranoia": 0.5
        }
        full_personality.update(personality)
        
        # Clamp values
        for trait in full_personality:
            full_personality[trait] = max(0.0, min(1.0, full_personality[trait]))
        
        npc_def = {
            "npc_id": name,
            "role": role,
            "location": location,
            "personality": full_personality,
            "initial_mood": self._select_initial_mood(full_personality),
            "initial_vitals": {
                "hunger": 0.2,
                "fatigue": 0.3
            },
            "backstory": backstory,
            "initial_memories": [
                {
                    "id": f"mem_{name}_001",
                    "memory_type": "belief",
                    "content": f"Core belief from backstory: {backstory[:100]}",
                    "strength": 0.8
                }
            ],
            "current_goal": "survive",
            "dialogue_style": dialogue_style,
            "faction": faction
        }
        
        self.generated_npcs[name] = npc_def
        return npc_def
    
    def _generate_personality(self, base_traits: Dict) -> Dict[str, float]:
        """Generate random personality with optional base traits"""
        personality = {}
        
        traits = ["curiosity", "empathy", "risk_tolerance", "aggression",
                 "discipline", "romanticism", "opportunism", "paranoia"]
        
        for trait in traits:
            if trait in base_traits:
                # Use constrained range for role-appropriate traits
                min_val, max_val = base_traits[trait]
                personality[trait] = round(random.uniform(min_val, max_val), 2)
            else:
                # Random value with slight bias towards middle
                personality[trait] = round(random.triangular(0.2, 0.8, 0.5), 2)
        
        return personality
    
    def _generate_name(self) -> str:
        """Generate a random NPC name"""
        first_names = [
            "Marcus", "Elena", "Kai", "Zara", "Dmitri", "Aria", "Cole", "Nora",
            "Jax", "Luna", "Rafe", "Iris", "Silas", "Maya", "Finn", "Sage"
        ]
        
        last_names = [
            "Cross", "Stone", "Rivers", "Steel", "Ash", "North", "West", "Gray",
            "Black", "White", "Green", "Vale", "Hunt", "Fox", "Wolf", "Hawk"
        ]
        
        # 60% chance of full name, 40% single name
        if random.random() < 0.6:
            return f"{random.choice(first_names)}_{random.choice(last_names)}"
        else:
            return random.choice(first_names)
    
    def _generate_backstory(self, name: str, role: str, location: str) -> str:
        """Generate a random backstory"""
        templates = [
            f"{name} has been working as a {role} at {location} for several years. Trust is earned through actions, not words.",
            f"A survivor who found purpose as a {role}. {name} protects {location} with unwavering dedication.",
            f"Former wanderer turned {role}. {name} knows the harsh realities of the wasteland and guards {location} carefully.",
            f"{name} arrived at {location} seeking safety and stayed to serve as {role}. Loyalty is paramount.",
            f"Experienced {role} at {location}. {name} has seen both the best and worst of humanity."
        ]
        return random.choice(templates)
    
    def _generate_initial_memories(self, name: str, role: str, location: str) -> List[Dict]:
        """Generate initial memories for NPC"""
        memories = [
            {
                "id": f"mem_{name}_001",
                "memory_type": "belief",
                "content": f"Trust must be earned through consistent actions.",
                "strength": round(random.uniform(0.7, 0.9), 2)
            },
            {
                "id": f"mem_{name}_002",
                "memory_type": "episodic",
                "content": f"First day at {location} - learned the importance of vigilance.",
                "strength": round(random.uniform(0.6, 0.8), 2)
            },
            {
                "id": f"mem_{name}_003",
                "memory_type": "social",
                "content": f"Working at {location} means dealing with all kinds of people.",
                "strength": round(random.uniform(0.5, 0.7), 2)
            }
        ]
        return memories
    
    def _select_initial_mood(self, personality: Dict) -> str:
        """Select initial mood based on personality"""
        if personality.get("paranoia", 0.5) > 0.7:
            return "Paranoid"
        elif personality.get("aggression", 0.5) > 0.7:
            return "Alert"
        elif personality.get("empathy", 0.5) > 0.7:
            return "Calm"
        elif personality.get("curiosity", 0.5) > 0.7:
            return "Curious"
        else:
            return "Neutral"
    
    def _select_goal(self, role_type: str) -> str:
        """Select appropriate goal based on role"""
        goal_map = {
            "gatekeeper": "secure_area",
            "guard": "maintain_order",
            "merchant": "maximize_profit",
            "civilian": "survive",
            "scholar": "gather_knowledge",
            "warrior": "protect_territory"
        }
        return goal_map.get(role_type, "survive")
    
    def save_npc_to_file(self, npc_id: str, directory: str = "/app/npc_system/persona"):
        """Save generated NPC to JSON file"""
        if npc_id not in self.generated_npcs:
            raise ValueError(f"NPC {npc_id} not found in generated NPCs")
        
        npc_def = self.generated_npcs[npc_id]
        filename = f"{directory}/{npc_id.lower()}_v1.json"
        
        with open(filename, 'w') as f:
            json.dump(npc_def, f, indent=2)
        
        return filename
    
    def get_npc_definition(self, npc_id: str) -> Dict:
        """Get NPC definition"""
        return self.generated_npcs.get(npc_id)

# Global generator instance
npc_generator = NPCGenerator()
