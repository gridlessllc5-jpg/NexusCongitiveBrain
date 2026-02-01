#!/usr/bin/env python3
"""Phase 3 Demo - Multi-NPC Interactions"""
import asyncio
import sys
sys.path.insert(0, '/app/npc_system')

from core.npc_system import NPCSystem
from core.multi_npc import orchestrator

async def phase3_demo():
    """Demonstrate multi-NPC system with factions"""
    print("\n" + "="*70)
    print("PHASE 3 DEMO: Multi-NPC & Faction System")
    print("="*70 + "\n")
    
    # Initialize 3 NPCs
    print("Initializing NPCs...")
    vera = NPCSystem("/app/npc_system/persona/vera_v1.json")
    guard = NPCSystem("/app/npc_system/persona/guard_v1.json")
    merchant = NPCSystem("/app/npc_system/persona/merchant_v1.json")
    
    # Register with orchestrator
    orchestrator.register_npc("Vera", vera, "guards")
    orchestrator.register_npc("Guard", guard, "guards")
    orchestrator.register_npc("Merchant", merchant, "traders")
    
    # Start autonomous systems
    await vera.start_autonomous_systems()
    await guard.start_autonomous_systems()
    await merchant.start_autonomous_systems()
    
    print("✓ 3 NPCs initialized\n")
    
    # Display faction status
    print("="*70)
    print("FACTION STATUS")
    print("="*70)
    faction_status = orchestrator.get_faction_status()
    for faction, data in faction_status.items():
        print(f"\n{faction.upper()}:")
        print(f"  Members: {', '.join(data['members'])}")
        print(f"  Count: {data['count']}")
        print(f"  Avg Internal Trust: {data['average_trust']:.2f}")
    
    # Display trust matrix
    print("\n" + "="*70)
    print("TRUST MATRIX (Initial)")
    print("="*70)
    for npc1 in ["Vera", "Guard", "Merchant"]:
        for npc2 in ["Vera", "Guard", "Merchant"]:
            if npc1 != npc2:
                trust = orchestrator.get_trust(npc1, npc2)
                print(f"  {npc1} → {npc2}: {trust:.2f}")
    
    # Scenario: Player interacts with Vera, then Vera communicates with Guard
    print("\n" + "="*70)
    print("SCENARIO 1: Player → Vera → Guard Communication")
    print("="*70 + "\n")
    
    # Player to Vera
    print("1. Player approaches Vera")
    player_action = "I have information about raiders near the east scrub"
    response = await vera.process_player_action(player_action)
    print(f"\nVera's thought: {response['cognitive_frame']['internal_reflection'][:100]}...")
    print(f"Vera says: {response['cognitive_frame']['dialogue']}")
    
    await asyncio.sleep(2)
    
    # Vera to Guard (NPC-to-NPC)
    print("\n2. Vera alerts Guard about threat")
    npc_interaction = await orchestrator.npc_to_npc_interaction(
        "Vera", "Guard",
        "Stranger reported raider activity near east scrub. Recommend patrol sweep."
    )
    guard_response = npc_interaction["response"]
    print(f"\nGuard's thought: {guard_response['cognitive_frame']['internal_reflection'][:100]}...")
    print(f"Guard says: {guard_response['cognitive_frame']['dialogue']}")
    print(f"Trust Vera→Guard: {orchestrator.get_trust('Guard', 'Vera'):.2f}")
    
    await asyncio.sleep(2)
    
    # Scenario: Player trades with Merchant
    print("\n" + "="*70)
    print("SCENARIO 2: Player → Merchant Trade")
    print("="*70 + "\n")
    
    player_action = "I want to trade ammunition for medical supplies"
    response = await merchant.process_player_action(player_action)
    print(f"\nMerchant's thought: {response['cognitive_frame']['internal_reflection'][:100]}...")
    print(f"Merchant says: {response['cognitive_frame']['dialogue']}")
    
    await asyncio.sleep(2)
    
    # Merchant tells Guard about new arrival
    print("\n3. Merchant informs Guard about new trader")
    npc_interaction = await orchestrator.npc_to_npc_interaction(
        "Merchant", "Guard",
        "New arrival completed a trade. Seemed legitimate, had quality ammunition."
    )
    guard_response = npc_interaction["response"]
    print(f"\nGuard acknowledges: {guard_response['cognitive_frame']['dialogue']}")
    
    # Final trust matrix
    print("\n" + "="*70)
    print("TRUST MATRIX (After Interactions)")
    print("="*70)
    for npc1 in ["Vera", "Guard", "Merchant"]:
        for npc2 in ["Vera", "Guard", "Merchant"]:
            if npc1 != npc2:
                trust = orchestrator.get_trust(npc1, npc2)
                print(f"  {npc1} → {npc2}: {trust:.2f}")
    
    # Cleanup
    vera.stop()
    guard.stop()
    merchant.stop()
    
    print("\n" + "="*70)
    print("PHASE 3 DEMO COMPLETE")
    print("="*70)
    print("\n✅ Multi-NPC orchestration functional")
    print("✅ Faction system operational")
    print("✅ NPC-to-NPC communication working")
    print("✅ Trust matrix tracking interactions\n")

if __name__ == "__main__":
    try:
        asyncio.run(phase3_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.\n")
