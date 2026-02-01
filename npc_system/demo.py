#!/usr/bin/env python3
"""Quick Demo - Automated interaction sequence"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/npc_system')

from core.npc_system import NPCSystem

async def run_demo():
    """Automated demo of NPC system"""
    print("\n" + "="*70)
    print("FRACTURED SURVIVAL - COGNITIVE NPC DEMO")
    print("Automated Interaction Sequence")
    print("="*70 + "\n")
    
    # Initialize Vera
    npc = NPCSystem("/app/npc_system/persona/vera_v1.json")
    await npc.start_autonomous_systems()
    
    # Scenario: Player approaches Porto Cobre Gates
    scenarios = [
        ("I approach slowly with my hands raised, showing I'm unarmed", 3),
        ("I say: 'I'm looking for shelter and willing to trade supplies'", 3),
        ("I pull out a medkit and offer it to Vera", 4),
        ("I ask: 'Have you seen any raiders nearby?'", 3),
        ("I thank Vera and prepare to enter the gates", 2)
    ]
    
    print("Scenario: Cautious Approach to Porto Cobre Gates\n")
    
    for i, (action, delay) in enumerate(scenarios, 1):
        print(f"\n{'='*70}")
        print(f"INTERACTION {i}/{len(scenarios)}")
        print(f"{'='*70}")
        
        response = await npc.process_player_action(action)
        npc.display_response(response)
        
        if i < len(scenarios):
            print(f"[Waiting {delay}s before next action...]")
            await asyncio.sleep(delay)
    
    # Show final state
    print(f"\n{'='*70}")
    print("FINAL STATE")
    print(f"{'='*70}\n")
    
    print("📊 Vera's Personality Evolution:")
    for trait, value in npc.personality.items():
        bar_length = int(value * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"  {trait.capitalize():15} {bar} {value:.3f}")
    
    print("\n💭 Summary Beliefs:")
    beliefs = npc.memory_vault.get_summary_beliefs(npc.npc_id, limit=5)
    for belief in beliefs:
        print(f"  • {belief}")
    
    print("\n🧠 Recent Memories:")
    memories = npc.memory_vault.get_recent_memories(npc.npc_id, limit=3)
    for mem in memories:
        print(f"  [{mem.memory_type}] {mem.content}")
    
    npc.stop()
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.\n")
