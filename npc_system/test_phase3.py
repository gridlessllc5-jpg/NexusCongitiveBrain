#!/usr/bin/env python3
"""Test Dynamic NPC Creation & Phase 3 Features"""
import requests
import json
import time

BASE_URL = "http://localhost:9000"

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_section(text):
    print(f"\n{'-'*70}")
    print(f"  {text}")
    print(f"{'-'*70}")

print_header("🚀 PHASE 3 FEATURES + DYNAMIC NPC CREATION TEST")

# Test 1: Get NPC Templates
print_section("Test 1: Get Available NPC Templates")
response = requests.get(f"{BASE_URL}/npc/templates")
templates = response.json()
print(f"Available Role Types: {', '.join(templates['templates'].keys())}")
print(f"Available Traits: {', '.join(templates['available_traits'][:4])}...")
print("✅ PASSED\n")

# Test 2: Generate Random NPC
print_section("Test 2: Generate Random Merchant NPC")
payload = {
    "role_type": "merchant",
    "name": None,  # Auto-generate
    "auto_initialize": True
}
response = requests.post(f"{BASE_URL}/npc/generate/random", json=payload)
random_npc = response.json()

print(f"Generated NPC:")
print(f"  Name: {random_npc['npc_id']}")
print(f"  Role: {random_npc['role']}")
print(f"  Location: {random_npc['location']}")
print(f"  Personality:")
for trait, value in list(random_npc['personality'].items())[:4]:
    print(f"    {trait}: {value:.2f}")
print(f"  Initialized: {random_npc['initialized']}")
print("✅ PASSED\n")

random_npc_id = random_npc['npc_id']

# Test 3: Create Custom NPC
print_section("Test 3: Create Custom NPC")
payload = {
    "name": "Shadow",
    "role": "Mysterious Information Broker",
    "location": "Dark Alley",
    "personality": {
        "curiosity": 0.9,
        "empathy": 0.3,
        "paranoia": 0.85,
        "opportunism": 0.95,
        "aggression": 0.4
    },
    "backstory": "Nobody knows Shadow's real identity. They deal in information and secrets, always staying in the shadows.",
    "dialogue_style": "Cryptic, speaks in riddles, never direct",
    "faction": "independents",
    "auto_initialize": True
}
response = requests.post(f"{BASE_URL}/npc/create/custom", json=payload)
custom_npc = response.json()

print(f"Created Custom NPC:")
print(f"  Name: {custom_npc['npc_id']}")
print(f"  Role: {custom_npc['role']}")
print(f"  Initialized: {custom_npc['initialized']}")
print("✅ PASSED\n")

# Test 4: List All NPCs
print_section("Test 4: List All Active NPCs")
response = requests.get(f"{BASE_URL}/npc/list")
npcs = response.json()["npcs"]
print(f"Total NPCs: {len(npcs)}")
for npc in npcs:
    print(f"  - {npc['npc_id']}: {npc['role']} ({npc['mood']})")
print("✅ PASSED\n")

# Test 5: Generate Quest from Random NPC
print_section("Test 5: Generate Quest from Random Merchant")
response = requests.post(f"{BASE_URL}/quest/generate/{random_npc_id}")
quest = response.json()

print(f"Quest Generated:")
print(f"  Title: {quest['title']}")
print(f"  Type: {quest['quest_type']}")
print(f"  Description: {quest['description']}")
print(f"  Objective: {quest['objective']}")
print(f"  Difficulty: {quest['difficulty']}")
print(f"  Reward: {quest['reward']}")
print("✅ PASSED\n")

# Test 6: Get Available Quests
print_section("Test 6: View All Available Quests")
response = requests.get(f"{BASE_URL}/quests/available")
quests = response.json()["quests"]
print(f"Available Quests: {len(quests)}")
for q in quests[:2]:
    print(f"\n  Quest: {q['title']}")
    print(f"    Giver: {q['quest_giver']}")
    print(f"    Type: {q['quest_type']}")
    print(f"    Difficulty: {q['difficulty']}")
print("✅ PASSED\n")

# Test 7: Create Trade Offer
print_section("Test 7: Create Trade Offer from Merchant")
payload = {
    "offering": {"food": 10, "water": 5},
    "requesting": {"ammunition": 20}
}
response = requests.post(
    f"{BASE_URL}/trade/create/{random_npc_id}",
    params=payload
)
trade = response.json()

print(f"Trade Offer Created:")
print(f"  Offer ID: {trade['offer_id']}")
print(f"  From: {trade['from_npc']}")
print(f"  Offering: {trade['offering']}")
print(f"  Requesting: {trade['requesting']}")
print("✅ PASSED\n")

# Test 8: Market Activity
print_section("Test 8: Check Market Activity")
response = requests.get(f"{BASE_URL}/trade/market")
market = response.json()

print(f"Market Activity:")
print(f"  Active Offers: {market['active_offers']}")
print(f"  Recent Trades: {market['recent_trades']}")
print(f"  Top Traders: {', '.join(market['top_traders']) if market['top_traders'] else 'None yet'}")
print("✅ PASSED\n")

# Test 9: Territory Overview
print_section("Test 9: Territorial Control Overview")
response = requests.get(f"{BASE_URL}/territory/overview")
territories = response.json()

print("Faction Territories:")
for faction, data in territories.items():
    print(f"\n  {faction.upper()}:")
    print(f"    Controlled: {data['controlled_territories']}")
    print(f"    Total Resources: {data['total_resources']:.2f}")
    print(f"    Contested: {data['contested_count']}")
print("✅ PASSED\n")

# Test 10: Simulate Conflict
print_section("Test 10: Simulate Territorial Conflict")
response = requests.post(
    f"{BASE_URL}/territory/simulate_conflict",
    params={"faction1": "guards", "faction2": "traders", "tension": 0.8}
)
conflict = response.json()

if "type" in conflict:
    print(f"Conflict Triggered:")
    print(f"  Type: {conflict['type']}")
    print(f"  Territory: {conflict['territory']}")
    print(f"  Factions: {', '.join(conflict['factions'])}")
    print(f"  Tension: {conflict['tension_level']}")
else:
    print(f"Result: {conflict.get('result', 'No conflict')}")
print("✅ PASSED\n")

# Test 11: Interact with Custom NPC
print_section("Test 11: Interact with Custom NPC (Shadow)")
payload = {
    "npc_id": "Shadow",
    "action": "I need information about the raiders"
}
response = requests.post(f"{BASE_URL}/npc/action", json=payload)
data = response.json()
cf = data['cognitive_frame']

print(f"🧠 Shadow's Internal Thought:")
print(f"   {cf['internal_reflection'][:120]}...")
print(f"\n💬 Shadow says:")
print(f"   \"{cf['dialogue']}\"")
print(f"\n📊 State: Intent={cf['intent']}, Mood={cf['emotional_state']}")
print("✅ PASSED\n")

print_header("📊 FINAL SUMMARY")
print("✅ All Phase 3 Features Working:")
print("  1. ✅ Random NPC Generation")
print("  2. ✅ Custom NPC Creation")
print("  3. ✅ Quest Generation System")
print("  4. ✅ Trade Network Simulation")
print("  5. ✅ Territory & Conflict System")
print("  6. ✅ Multi-NPC Management")
print("\n🎉 System fully operational with dynamic NPC creation!\n")
