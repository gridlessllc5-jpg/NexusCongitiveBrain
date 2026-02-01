"""Cognitive Brain - LLM Integration & Decision Making (Step 3)"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Use OpenAI-compatible adapter instead of emergentintegrations
# This works on both local and Cloudflare Workers deployments
try:
    from core.llm_adapter import LlmChat, UserMessage
except ImportError:
    from llm_adapter import LlmChat, UserMessage

# Load environment variables
load_dotenv("/app/npc_system/.env")

class CognitiveBrain:
    """NPC Brain - Handles perception, reflection, and decision-making using LLM"""
    
    def __init__(self, npc_id: str, personality: Dict, memory_vault, limbic_system):
        self.npc_id = npc_id
        self.personality = personality
        self.memory_vault = memory_vault
        self.limbic = limbic_system
        
        # Initialize LLM - supports both OPENAI_API_KEY and EMERGENT_LLM_KEY
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
        self.llm = LlmChat(
            api_key=api_key,
            session_id=f"npc_{npc_id}_{datetime.now().timestamp()}",
            system_message=self._build_system_prompt()
        ).with_model("openai", "gpt-4o")
        
        print(f"✓ Brain initialized for {npc_id} with GPT-4o")
    
    def _build_system_prompt(self) -> str:
        """Build NPC system prompt with personality and world context"""
        return f"""You are {self.npc_id}, an NPC in the post-apocalyptic world of Fractured Survival.

PERSONALITY TRAITS (0.0-1.0 scale):
- Curiosity: {self.personality.get('curiosity', 0.5)}
- Empathy: {self.personality.get('empathy', 0.5)}
- Aggression: {self.personality.get('aggression', 0.5)}
- Anxiety/Paranoia: {self.personality.get('paranoia', 0.5)}
- Discipline: {self.personality.get('discipline', 0.5)}
- Romanticism: {self.personality.get('romanticism', 0.5)}
- Opportunism: {self.personality.get('opportunism', 0.5)}

ROLE & CONTEXT:
You are stationed at Porto Cobre Gates, a dangerous frontier. Resources are scarce, trust is rare.

CRITICAL INSTRUCTIONS:
1. Generate responses in STRICT JSON format with these exact fields:
   - internal_reflection: Your private thoughts (string)
   - intent: Your action goal (one of: Investigate, Flee, Assist, Ignore, Socialize, Guard, Trade)
   - dialogue: Your spoken words (string, can be empty if you stay silent)
   - urgency: Action priority (float 0.0-1.0)
   - trust_mod: Trust change for the player (float, -0.1 to +0.1, optional)
   - emotional_state: Your current mood (string)

2. Your internal_reflection should be detailed and consider:
   - Your personality traits
   - Past memories
   - Current vitals (hunger, fatigue)
   - The player's action and its implications

3. Your dialogue should reflect your personality. High paranoia = guarded speech.

4. ALWAYS respond with valid JSON only. No additional text.

Example response:
{{
  "internal_reflection": "He's approaching with a weapon visible. Given my paranoia (0.8), I should be cautious. But he's not pointing it at me...",
  "intent": "Investigate",
  "dialogue": "State your business, stranger. And keep that weapon sheathed.",
  "urgency": 0.7,
  "trust_mod": -0.02,
  "emotional_state": "Wary"
}}"""
    
    async def process_perception(self, perception: str, context: Dict = None) -> Dict:
        """Process player action through cognitive loop"""
        # Build context
        memories = self.memory_vault.get_recent_memories(self.npc_id, limit=3)
        beliefs = self.memory_vault.get_summary_beliefs(self.npc_id, limit=3)
        limbic_state = self.limbic.get_state_summary()
        
        # Build prompt
        prompt = f"""CURRENT SITUATION:
Perception: {perception}

YOUR STATE:
- Vitals: Hunger {limbic_state['vitals']['hunger']:.1f}, Fatigue {limbic_state['vitals']['fatigue']:.1f}
- Mood: {limbic_state['emotional_state']['mood']}
- Arousal: {limbic_state['emotional_state']['arousal']:.1f}

RECENT MEMORIES:
{self._format_memories(memories)}

BELIEFS:
{self._format_beliefs(beliefs)}

Respond with your cognitive frame in JSON format as instructed."""
        
        # Simulate think time
        think_time = self.limbic.get_think_time()
        await asyncio.sleep(think_time * 0.1)  # Scaled for demo
        
        # Query LLM
        try:
            response = await self.llm.send_message(UserMessage(text=prompt))
            
            # Parse JSON
            cognitive_frame = json.loads(response)
            
            # Validate required fields
            required = ["internal_reflection", "intent", "dialogue", "urgency", "emotional_state"]
            if not all(field in cognitive_frame for field in required):
                raise ValueError("Missing required fields in cognitive frame")
            
            return cognitive_frame
            
        except Exception as e:
            print(f"⚠ Error in cognitive processing: {e}")
            # Fallback response
            return {
                "internal_reflection": f"[ERROR: {str(e)}] Defaulting to cautious behavior.",
                "intent": "Guard",
                "dialogue": "...",
                "urgency": 0.5,
                "emotional_state": "Confused"
            }
    
    async def autonomous_reflection(self):
        """Background reflection on recent events (Thread B trigger)"""
        memories = self.memory_vault.get_recent_memories(self.npc_id, limit=5)
        
        if not memories:
            return
        
        prompt = f"""AUTONOMOUS REFLECTION (Background Thinking):
Review your last 5 memories and generate a summary belief about the current situation.

RECENT MEMORIES:
{self._format_memories(memories)}

Generate a single-sentence belief or insight based on these memories.
Respond ONLY with the belief text, no JSON, no extra formatting."""
        
        try:
            belief = await self.llm.send_message(UserMessage(text=prompt))
            self.memory_vault.save_summary_belief(self.npc_id, belief.strip(), strength=0.7)
            print(f"  ✓ New Belief: '{belief.strip()}'")
        except Exception as e:
            print(f"  ⚠ Reflection error: {e}")
    
    def _format_memories(self, memories: List) -> str:
        """Format memories for prompt"""
        if not memories:
            return "- No recent memories"
        return "\n".join([f"- [{m.memory_type}] {m.content}" for m in memories])
    
    def _format_beliefs(self, beliefs: List[str]) -> str:
        """Format beliefs for prompt"""
        if not beliefs:
            return "- No established beliefs yet"
        return "\n".join([f"- {b}" for b in beliefs])
