#!/usr/bin/env python3
"""Headless Terminal Simulation - Step 4: CLI Interface"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from core.npc_system import NPCSystem


class HeadlessSimulation:
    """Interactive CLI for testing NPC system"""
    
    def __init__(self):
        self.npc = None
        self.running = False
    
    async def initialize(self):
        """Load Vera NPC"""
        persona_path = "/app/npc_system/persona/vera_v1.json"
        self.npc = NPCSystem(persona_path)
        await self.npc.start_autonomous_systems()
    
    def print_welcome(self):
        """Display welcome message"""
        print("\n" + "="*70)
        print("FRACTURED SURVIVAL - COGNITIVE NPC SIMULATION")
        print("="*70)
        print("\nYou are approaching the Porto Cobre Gates.")
        print("Vera, the gatekeeper, watches you with suspicious eyes.\n")
        print("Commands:")
        print("  - Type any action (e.g., 'I wave hello', 'I draw my weapon')")
        print("  - 'status' - View Vera's current state")
        print("  - 'memories' - View Vera's recent memories")
        print("  - 'beliefs' - View Vera's beliefs")
        print("  - 'personality' - View Vera's personality traits")
        print("  - 'quit' or 'exit' - End simulation")
        print("="*70 + "\n")
    
    async def run(self):
        """Main simulation loop"""
        await self.initialize()
        self.print_welcome()
        self.running = True
        
        try:
            while self.running:
                # Get player input
                try:
                    user_input = input(">>> You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n")
                    break
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'status':
                    self.show_status()
                elif user_input.lower() == 'memories':
                    self.show_memories()
                elif user_input.lower() == 'beliefs':
                    self.show_beliefs()
                elif user_input.lower() == 'personality':
                    self.show_personality()
                else:
                    # Process as player action
                    response = await self.npc.process_player_action(user_input)
                    self.npc.display_response(response)
        
        finally:
            self.npc.stop()
            print("\nSimulation ended. Thank you for testing!\n")
    
    def show_status(self):
        """Display NPC status"""
        limbic_state = self.npc.limbic.get_state_summary()
        print(f"\n📊 VERA'S STATUS:")
        print(f"   Mood: {limbic_state['emotional_state']['mood']}")
        print(f"   Arousal: {limbic_state['emotional_state']['arousal']:.2f}")
        print(f"   Hunger: {limbic_state['vitals']['hunger']:.2f}")
        print(f"   Fatigue: {limbic_state['vitals']['fatigue']:.2f}")
        print(f"   Think Time: {limbic_state['think_time']:.2f}s\n")
    
    def show_memories(self):
        """Display recent memories"""
        memories = self.npc.memory_vault.get_recent_memories(self.npc.npc_id, limit=5)
        print(f"\n🧠 VERA'S RECENT MEMORIES:")
        if memories:
            for mem in memories:
                print(f"   [{mem.memory_type}] {mem.content} (strength: {mem.strength:.2f})")
        else:
            print("   No memories yet.")
        print()
    
    def show_beliefs(self):
        """Display beliefs"""
        beliefs = self.npc.memory_vault.get_summary_beliefs(self.npc.npc_id, limit=5)
        print(f"\n💭 VERA'S BELIEFS:")
        if beliefs:
            for belief in beliefs:
                print(f"   • {belief}")
        else:
            print("   No beliefs formed yet.")
        print()
    
    def show_personality(self):
        """Display personality traits"""
        print(f"\n🎭 VERA'S PERSONALITY:")
        for trait, value in self.npc.personality.items():
            bar_length = int(value * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"   {trait.capitalize():15} {bar} {value:.2f}")
        print()


async def main():
    """Entry point"""
    sim = HeadlessSimulation()
    await sim.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.\n")
        sys.exit(0)
