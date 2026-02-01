"""
Backend API Tests for Phase 4: Dynamic Civilizations
Tests: Factions, Faction Events, Territory Control, Trade Routes, Battles
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFactions:
    """Factions API endpoint tests"""
    
    def test_get_all_factions(self):
        """Test GET /api/factions returns all faction details"""
        response = requests.get(f"{BASE_URL}/api/factions")
        assert response.status_code == 200
        data = response.json()
        
        # Verify factions structure
        assert isinstance(data, dict)
        # Should have factions data
        print(f"Factions response: {data}")
    
    def test_get_faction_details(self):
        """Test GET /api/faction/{faction_id} returns faction details"""
        # Test with known faction
        response = requests.get(f"{BASE_URL}/api/faction/guards")
        assert response.status_code == 200
        data = response.json()
        print(f"Guards faction details: {data}")


class TestFactionEvents:
    """Faction Events API endpoint tests"""
    
    def test_get_faction_events(self):
        """Test GET /api/faction/events returns recent events"""
        response = requests.get(f"{BASE_URL}/api/faction/events")
        assert response.status_code == 200
        data = response.json()
        
        # Verify events structure
        assert "events" in data
        assert isinstance(data["events"], list)
        print(f"Faction events: {data}")
    
    def test_get_faction_events_with_limit(self):
        """Test GET /api/faction/events with limit parameter"""
        response = requests.get(f"{BASE_URL}/api/faction/events?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
    
    def test_trigger_faction_event(self):
        """Test POST /api/faction/event triggers a faction event"""
        response = requests.post(
            f"{BASE_URL}/api/faction/event",
            params={
                "event_type": "skirmish",
                "faction1": "guards",
                "faction2": "outcasts",
                "description": "Test skirmish event"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "event_triggered"
        print(f"Triggered event: {data}")


class TestTerritoryControl:
    """Territory Control API endpoint tests"""
    
    def test_get_territory_control(self):
        """Test GET /api/territory/control returns territory control status"""
        response = requests.get(f"{BASE_URL}/api/territory/control")
        assert response.status_code == 200
        data = response.json()
        
        # Verify territories structure
        assert "territories" in data
        assert isinstance(data["territories"], dict)
        
        # Check territory data structure
        for territory_id, territory_data in data["territories"].items():
            assert "name" in territory_data
            assert "controlling_faction" in territory_data
            assert "control_strength" in territory_data
            assert "strategic_value" in territory_data
        
        print(f"Territory control: {data}")


class TestTradeRoutes:
    """Trade Routes API endpoint tests"""
    
    def test_get_trade_routes(self):
        """Test GET /api/traderoutes returns trade routes"""
        response = requests.get(f"{BASE_URL}/api/traderoutes")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "routes" in data
        assert "total" in data
        assert isinstance(data["routes"], list)
        print(f"Trade routes: {data}")
    
    def test_establish_trade_route(self):
        """Test POST /api/traderoute/establish creates new route"""
        response = requests.post(
            f"{BASE_URL}/api/traderoute/establish",
            params={
                "from_npc": "merchant",
                "to_npc": "vera"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify route was created
        assert "status" in data
        assert data["status"] == "route_established"
        assert "route" in data
        assert "route_id" in data["route"]
        
        # Store route_id for later tests
        TestTradeRoutes.created_route_id = data["route"]["route_id"]
        print(f"Established route: {data}")
    
    def test_execute_trade(self):
        """Test POST /api/traderoute/{route_id}/execute executes trade"""
        # First get active routes only
        routes_response = requests.get(f"{BASE_URL}/api/traderoutes?status=active")
        routes = routes_response.json().get("routes", [])
        
        if routes:
            route_id = routes[0]["route_id"]
            response = requests.post(f"{BASE_URL}/api/traderoute/{route_id}/execute")
            assert response.status_code == 200
            data = response.json()
            
            # Trade can succeed or be disrupted by risk
            assert "route_id" in data or "error" in data
            print(f"Trade execution result: {data}")
        else:
            # Create a new route and execute it
            establish_response = requests.post(
                f"{BASE_URL}/api/traderoute/establish",
                params={"from_npc": "merchant", "to_npc": "guard"}
            )
            if establish_response.status_code == 200:
                route_id = establish_response.json()["route"]["route_id"]
                response = requests.post(f"{BASE_URL}/api/traderoute/{route_id}/execute")
                assert response.status_code == 200
                data = response.json()
                assert "route_id" in data or "error" in data
                print(f"Trade execution result: {data}")
            else:
                pytest.skip("No active trade routes available to execute")
    
    def test_disrupt_trade_route(self):
        """Test POST /api/traderoute/{route_id}/disrupt disrupts route"""
        # Get active routes
        routes_response = requests.get(f"{BASE_URL}/api/traderoutes?status=active")
        routes = routes_response.json().get("routes", [])
        
        if routes:
            route_id = routes[0]["route_id"]
            response = requests.post(
                f"{BASE_URL}/api/traderoute/{route_id}/disrupt",
                params={"reason": "test_attack"}
            )
            assert response.status_code == 200
            data = response.json()
            print(f"Disrupt result: {data}")
        else:
            pytest.skip("No active trade routes to disrupt")


class TestBattles:
    """Battles API endpoint tests"""
    
    def test_get_battle_history(self):
        """Test GET /api/battles returns battle history"""
        response = requests.get(f"{BASE_URL}/api/battles")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "battles" in data
        assert "total" in data
        assert isinstance(data["battles"], list)
        print(f"Battle history: {data}")
    
    def test_initiate_battle(self):
        """Test POST /api/territory/{territory}/battle initiates battle"""
        # Get territory control to find a territory to attack
        control_response = requests.get(f"{BASE_URL}/api/territory/control")
        territories = control_response.json().get("territories", {})
        
        # Find a territory not controlled by outcasts
        target_territory = None
        for territory_id, territory_data in territories.items():
            if territory_data.get("controlling_faction") != "outcasts":
                target_territory = territory_id
                break
        
        if target_territory:
            response = requests.post(
                f"{BASE_URL}/api/territory/{target_territory}/battle",
                params={"attacker_faction": "outcasts"}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify battle was initiated
            assert "status" in data
            assert data["status"] == "battle_initiated"
            assert "battle" in data
            assert "battle_id" in data["battle"]
            
            # Store battle_id for resolve test
            TestBattles.created_battle_id = data["battle"]["battle_id"]
            print(f"Initiated battle: {data}")
        else:
            pytest.skip("No suitable territory to attack")
    
    def test_resolve_battle(self):
        """Test POST /api/battle/{battle_id}/resolve resolves battle"""
        # Get pending battles
        battles_response = requests.get(f"{BASE_URL}/api/battles")
        battles = battles_response.json().get("battles", [])
        
        # Find an in_progress battle
        pending_battle = None
        for battle in battles:
            if battle.get("status") == "in_progress":
                pending_battle = battle
                break
        
        if pending_battle:
            battle_id = pending_battle["battle_id"]
            response = requests.post(f"{BASE_URL}/api/battle/{battle_id}/resolve")
            assert response.status_code == 200
            data = response.json()
            
            # Verify battle was resolved
            assert "battle_id" in data
            assert "winner" in data
            assert "status" in data
            print(f"Resolved battle: {data}")
        else:
            pytest.skip("No in_progress battles to resolve")


class TestFactionRelations:
    """Faction Relations API endpoint tests"""
    
    def test_get_faction_relation(self):
        """Test GET /api/faction/relation/{faction1}/{faction2}"""
        response = requests.get(f"{BASE_URL}/api/faction/relation/guards/outcasts")
        assert response.status_code == 200
        data = response.json()
        
        # Verify relation structure
        assert "faction1" in data
        assert "faction2" in data
        assert "score" in data
        assert "type" in data
        print(f"Faction relation: {data}")


class TestNPCGoals:
    """NPC Goals API endpoint tests"""
    
    def test_generate_npc_goal(self):
        """Test POST /api/npc/{npc_id}/goal/generate"""
        # First ensure vera is initialized
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        response = requests.post(
            f"{BASE_URL}/api/npc/vera/goal/generate",
            params={"faction": "guards"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify goal structure
        assert "status" in data
        assert data["status"] == "goal_generated"
        assert "goal" in data
        assert "goal_id" in data["goal"]
        assert "type" in data["goal"]
        assert "description" in data["goal"]
        print(f"Generated goal: {data}")
    
    def test_get_npc_goals(self):
        """Test GET /api/npc/{npc_id}/goals"""
        response = requests.get(f"{BASE_URL}/api/npc/vera/goals")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "npc_id" in data
        assert "goals" in data
        assert isinstance(data["goals"], list)
        print(f"NPC goals: {data}")


class TestQuestChains:
    """Quest Chains API endpoint tests"""
    
    def test_create_quest_chain(self):
        """Test POST /api/questchain/create/{npc_id}"""
        response = requests.post(
            f"{BASE_URL}/api/questchain/create/vera",
            params={"faction": "guards"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify chain structure
        assert "status" in data
        assert data["status"] == "chain_created"
        assert "chain" in data
        assert "chain_id" in data["chain"]
        assert "name" in data["chain"]
        print(f"Created quest chain: {data}")
    
    def test_get_quest_chains(self):
        """Test GET /api/questchains"""
        response = requests.get(f"{BASE_URL}/api/questchains")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "chains" in data
        assert "total" in data
        assert isinstance(data["chains"], list)
        print(f"Quest chains: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
