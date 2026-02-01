"""Limbic System - Emotional & Vitals Management (Step 2)"""
import time
import asyncio
from datetime import datetime
from typing import Dict
from dataclasses import dataclass, field

@dataclass
class Vitals:
    """NPC biological constraints"""
    hunger: float = 0.2  # 0.0 = full, 1.0 = starving
    fatigue: float = 0.3  # 0.0 = rested, 1.0 = exhausted
    
    def decay(self, delta_seconds: float):
        """Natural vitals decay over time"""
        self.hunger = min(1.0, self.hunger + (delta_seconds / 14400))  # 4 hours to starve
        self.fatigue = min(1.0, self.fatigue + (delta_seconds / 21600))  # 6 hours to exhaust

@dataclass
class EmotionalState:
    """NPC emotional state"""
    mood: str = "Calm"  # Calm, Paranoid, Aggressive, Fearful, Happy
    arousal: float = 0.5  # 0.0 = lethargic, 1.0 = panicked
    valence: float = 0.5  # 0.0 = negative, 1.0 = positive
    
    def update_from_event(self, event_type: str, intensity: float):
        """Update emotional state based on events"""
        if event_type == "threat":
            self.arousal = min(1.0, self.arousal + intensity)
            self.valence = max(0.0, self.valence - intensity)
            if self.arousal > 0.7:
                self.mood = "Paranoid"
        elif event_type == "positive":
            self.valence = min(1.0, self.valence + intensity)
            self.arousal = max(0.0, self.arousal - intensity * 0.5)
            if self.valence > 0.7:
                self.mood = "Happy"
        
        # Natural decay towards baseline
        self.arousal = self.arousal * 0.95
        self.valence = 0.5 + (self.valence - 0.5) * 0.9

class LimbicSystem:
    """Manages emotions, vitals, and autonomous reflection (Thread B)"""
    
    def __init__(self, npc_id: str):
        self.npc_id = npc_id
        self.vitals = Vitals()
        self.emotional_state = EmotionalState()
        self.last_reflection_time = time.time()
        self.reflection_interval = 300  # 300 seconds (5 minutes)
        self.running = False
    
    def get_think_time(self) -> float:
        """Simulated sensory latency based on arousal"""
        if self.emotional_state.arousal > 0.8:
            return 0.1  # Nearly instant when panicked
        elif self.emotional_state.arousal < 0.3:
            return 2.0  # Slow when calm
        else:
            return 1.0  # Normal
    
    def needs_reflection(self) -> bool:
        """Check if autonomous reflection is due"""
        return (time.time() - self.last_reflection_time) >= self.reflection_interval
    
    async def autonomous_loop(self, brain_callback):
        """Thread B: Background vitals decay & autonomous reflection"""
        self.running = True
        last_decay = time.time()
        
        while self.running:
            # Vitals decay
            now = time.time()
            delta = now - last_decay
            self.vitals.decay(delta)
            last_decay = now
            
            # Check for autonomous reflection
            if self.needs_reflection():
                print(f"\n[Thread B] 🧠 Autonomous Reflection triggered for {self.npc_id}")
                await brain_callback()  # Trigger brain reflection
                self.last_reflection_time = now
            
            await asyncio.sleep(1)  # Check every second
    
    def stop(self):
        """Stop the autonomous loop"""
        self.running = False
    
    def get_state_summary(self) -> Dict:
        """Get current limbic state"""
        return {
            "vitals": {
                "hunger": round(self.vitals.hunger, 2),
                "fatigue": round(self.vitals.fatigue, 2)
            },
            "emotional_state": {
                "mood": self.emotional_state.mood,
                "arousal": round(self.emotional_state.arousal, 2),
                "valence": round(self.emotional_state.valence, 2)
            },
            "think_time": round(self.get_think_time(), 2)
        }
