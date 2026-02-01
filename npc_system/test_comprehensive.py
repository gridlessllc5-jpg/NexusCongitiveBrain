#!/usr/bin/env python3
"""Comprehensive Test Suite for Standalone NPC Service"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:9000"

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_section(text):
    print(f"\n{'─'*70}")
    print(f"  {text}")
    print(f"{'─'*70}")

def test_health_check():
    print_section("Test 1: Health Check")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    assert response.json()["status"] == "operational"
    print("✅ PASSED")

def test_initialize_vera():
    print_section("Test 2: Initialize Vera")
    payload = {"npc_id": "vera"}
    response = requests.post(f"{BASE_URL}/npc/init", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    assert response.status_code == 200
    assert data["npc_id"] == "vera"
    print("✅ PASSED")
    return data

def test_initialize_guard():
    print_section("Test 3: Initialize Guard")
    payload = {"npc_id": "guard"}
    response = requests.post(f"{BASE_URL}/npc/init", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Initialized: {data['npc_id']} - {data['role']}")
    assert response.status_code == 200
    print("✅ PASSED")

def test_initialize_merchant():
    print_section("Test 4: Initialize Merchant")
    payload = {"npc_id": "merchant"}
    response = requests.post(f"{BASE_URL}/npc/init", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Initialized: {data['npc_id']} - {data['role']}")
    assert response.status_code == 200
    print("✅ PASSED")

def test_list_npcs():
    print_section("Test 5: List Active NPCs")
    response = requests.get(f"{BASE_URL}/npc/list")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Active NPCs: {len(data['npcs'])}")
    for npc in data['npcs']:
        print(f"  - {npc['npc_id']}: {npc['role']} ({npc['mood']})")
    assert len(data['npcs']) == 3
    print("✅ PASSED")

def test_player_action_vera():
    print_section("Test 6: Player Action → Vera (Peaceful)")
    payload = {
        "npc_id": "vera",
        "action": "I approach slowly with my hands raised, showing I'm unarmed"
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/npc/action", json=payload)
    response_time = time.time() - start_time
    
    print(f"Status: {response.status_code}")
    print(f"Response Time: {response_time:.2f}s")
    
    data = response.json()
    cf = data['cognitive_frame']
    
    print(f"\n🧠 Internal Thought:")
    print(f"   {cf['internal_reflection'][:150]}...")
    print(f"\n💬 Vera says:")
    print(f"   \"{cf['dialogue']}\"")
    print(f"\n📊 State:")
    print(f"   Intent: {cf['intent']} | Urgency: {cf['urgency']:.1f}")
    print(f"   Mood: {cf['emotional_state']}")
    print(f"   Hunger: {data['limbic_state']['vitals']['hunger']:.2f}")
    print(f"   Fatigue: {data['limbic_state']['vitals']['fatigue']:.2f}")
    
    assert response.status_code == 200
    assert cf['dialogue'] is not None
    print("✅ PASSED")
    return response_time

def test_player_action_vera_threat():
    print_section("Test 7: Player Action → Vera (Threat)")
    payload = {
        "npc_id": "vera",
        "action": "I suddenly draw my weapon and point it at Vera"
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/npc/action", json=payload)
    response_time = time.time() - start_time
    
    data = response.json()
    cf = data['cognitive_frame']
    
    print(f"Response Time: {response_time:.2f}s")
    print(f"\n🧠 Internal Thought:")
    print(f"   {cf['internal_reflection'][:150]}...")
    print(f"\n💬 Vera says:")
    print(f"   \"{cf['dialogue']}\"")
    print(f"\n📊 State:")
    print(f"   Intent: {cf['intent']} | Urgency: {cf['urgency']:.1f}")
    print(f"   Mood: {cf['emotional_state']}")
    
    assert cf['urgency'] > 0.7  # High urgency for threat
    print("✅ PASSED - Vera reacted appropriately to threat")
    return response_time

def test_guard_action():
    print_section("Test 8: Player Action → Guard")
    payload = {
        "npc_id": "guard",
        "action": "I ask the guard about the security protocols"
    }
    
    response = requests.post(f"{BASE_URL}/npc/action", json=payload)
    data = response.json()
    cf = data['cognitive_frame']
    
    print(f"\n💬 Guard says:")
    print(f"   \"{cf['dialogue']}\"")
    print(f"   Mood: {cf['emotional_state']}")
    
    assert response.status_code == 200
    print("✅ PASSED")

def test_merchant_action():
    print_section("Test 9: Player Action → Merchant")
    payload = {
        "npc_id": "merchant",
        "action": "I want to trade supplies for ammunition"
    }
    
    response = requests.post(f"{BASE_URL}/npc/action", json=payload)
    data = response.json()
    cf = data['cognitive_frame']
    
    print(f"\n💬 Merchant says:")
    print(f"   \"{cf['dialogue']}\"")
    print(f"   Mood: {cf['emotional_state']}")
    
    assert response.status_code == 200
    print("✅ PASSED")

def test_npc_status():
    print_section("Test 10: Get NPC Status (Vera)")
    response = requests.get(f"{BASE_URL}/npc/status/vera")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"NPC: {data['npc_id']}")
    print(f"Active: {data['active']}")
    print(f"Vitals: Hunger={data['vitals']['hunger']:.2f}, Fatigue={data['vitals']['fatigue']:.2f}")
    print(f"Mood: {data['emotional_state']['mood']} (Arousal: {data['emotional_state']['arousal']:.2f})")
    
    print(f"\nPersonality Traits:")
    for trait, value in list(data['personality'].items())[:4]:
        print(f"  {trait}: {value:.2f}")
    
    assert response.status_code == 200
    print("✅ PASSED")

def test_npc_memories():
    print_section("Test 11: Get NPC Memories (Vera)")
    response = requests.get(f"{BASE_URL}/npc/memories/vera?limit=5")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Memories Count: {len(data['memories'])}")
    
    for i, mem in enumerate(data['memories'][:3], 1):
        print(f"\n  Memory {i} [{mem['type']}]:")
        print(f"    {mem['content'][:80]}...")
        print(f"    Strength: {mem['strength']:.2f}")
    
    assert response.status_code == 200
    assert len(data['memories']) > 0
    print("✅ PASSED")

def test_factions():
    print_section("Test 12: Get Faction Status")
    response = requests.get(f"{BASE_URL}/factions")
    data = response.json()
    
    print(f"Status: {response.status_code}")
    for faction, info in data.items():
        print(f"\n{faction.upper()}:")
        print(f"  Members: {', '.join(info['members'])}")
        print(f"  Count: {info['count']}")
        print(f"  Avg Trust: {info['average_trust']:.2f}")
    
    assert response.status_code == 200
    print("✅ PASSED")

def test_trust_matrix():
    print_section("Test 13: Trust Between NPCs")
    pairs = [("vera", "guard"), ("guard", "merchant"), ("vera", "merchant")]
    
    for npc1, npc2 in pairs:
        response = requests.get(f"{BASE_URL}/trust/{npc1}/{npc2}")
        data = response.json()
        print(f"{npc1} → {npc2}: Trust = {data['trust']:.2f}")
    
    print("✅ PASSED")

def test_performance():
    print_section("Test 14: Performance Test")
    print("Testing 5 consecutive actions...")
    
    times = []
    for i in range(5):
        payload = {
            "npc_id": "vera",
            "action": f"Test action #{i+1}"
        }
        start = time.time()
        response = requests.post(f"{BASE_URL}/npc/action", json=payload)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Action {i+1}: {elapsed:.2f}s")
    
    avg_time = sum(times) / len(times)
    print(f"\nAverage Response Time: {avg_time:.2f}s")
    print(f"Min: {min(times):.2f}s | Max: {max(times):.2f}s")
    
    assert avg_time < 5.0  # Should be under 5 seconds
    print("✅ PASSED")

def run_all_tests():
    print_header("🧪 FRACTURED SURVIVAL - NPC SERVICE TEST SUITE")
    print(f"Testing service at: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        test_health_check,
        test_initialize_vera,
        test_initialize_guard,
        test_initialize_merchant,
        test_list_npcs,
        test_player_action_vera,
        test_player_action_vera_threat,
        test_guard_action,
        test_merchant_action,
        test_npc_status,
        test_npc_memories,
        test_factions,
        test_trust_matrix,
        test_performance
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            failed += 1
    
    print_header("📊 TEST RESULTS")
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Service is fully operational.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review errors above.")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_all_tests()
