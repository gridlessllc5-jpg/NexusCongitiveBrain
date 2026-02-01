"""
Backend API Tests for Fractured Survival NPC System
Tests: NPC initialization, action with player tracking, player info, players list, NPC relationships
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"


class TestNPCInit:
    """NPC initialization endpoint tests"""
    
    def test_init_vera_npc(self):
        """Test initializing vera NPC"""
        response = requests.post(
            f"{BASE_URL}/api/npc/init",
            json={"npc_id": "vera"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should be initialized or already_exists
        assert data["status"] in ["initialized", "already_exists"]
        assert data["npc_id"] == "vera"
    
    def test_init_guard_npc(self):
        """Test initializing guard NPC"""
        response = requests.post(
            f"{BASE_URL}/api/npc/init",
            json={"npc_id": "guard"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["initialized", "already_exists"]
        assert data["npc_id"] == "guard"
    
    def test_init_merchant_npc(self):
        """Test initializing merchant NPC"""
        response = requests.post(
            f"{BASE_URL}/api/npc/init",
            json={"npc_id": "merchant"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["initialized", "already_exists"]
        assert data["npc_id"] == "merchant"


class TestNPCAction:
    """NPC action endpoint tests - player tracking and reputation"""
    
    def test_action_returns_player_id(self):
        """Test that action returns player_id"""
        test_player_id = f"TEST_player_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "vera",
                "action": "Hello, I am a friendly traveler",
                "player_id": test_player_id,
                "player_name": "TestPlayer"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify player_id is returned
        assert "player_id" in data
        assert data["player_id"] == test_player_id
    
    def test_action_returns_reputation(self):
        """Test that action returns reputation"""
        test_player_id = f"TEST_player_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "vera",
                "action": "I come in peace",
                "player_id": test_player_id,
                "player_name": "PeacefulTraveler"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify reputation is returned
        assert "reputation" in data
        assert isinstance(data["reputation"], (int, float))
    
    def test_action_returns_reputation_change(self):
        """Test that action returns reputation change (trust_mod)"""
        test_player_id = f"TEST_player_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "vera",
                "action": "I want to help the settlement",
                "player_id": test_player_id,
                "player_name": "HelperPlayer"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify cognitive_frame contains trust_mod
        assert "cognitive_frame" in data
        assert "trust_mod" in data["cognitive_frame"]
        assert isinstance(data["cognitive_frame"]["trust_mod"], (int, float))
    
    def test_action_returns_cognitive_frame(self):
        """Test that action returns full cognitive frame"""
        test_player_id = f"TEST_player_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "vera",
                "action": "What is this place?",
                "player_id": test_player_id,
                "player_name": "CuriousPlayer"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify cognitive_frame structure
        assert "cognitive_frame" in data
        cf = data["cognitive_frame"]
        assert "internal_reflection" in cf
        assert "intent" in cf
        assert "dialogue" in cf
        assert "emotional_state" in cf
    
    def test_action_with_nonexistent_npc(self):
        """Test action with non-existent NPC returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "nonexistent_npc_xyz",
                "action": "Hello",
                "player_id": "test_player"
            }
        )
        assert response.status_code == 404


class TestPlayerInfo:
    """Player info endpoint tests"""
    
    def test_get_player_info(self):
        """Test getting player info"""
        # First create a player by interacting
        test_player_id = f"TEST_player_{uuid.uuid4().hex[:8]}"
        requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "vera",
                "action": "Hello",
                "player_id": test_player_id,
                "player_name": "InfoTestPlayer"
            }
        )
        
        # Now get player info
        response = requests.get(f"{BASE_URL}/api/player/{test_player_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify player info structure
        assert "player_id" in data
        assert data["player_id"] == test_player_id
        assert "player_name" in data
        assert "total_interactions" in data
        assert "global_reputation" in data
        assert "npc_reputations" in data
        assert "rumors" in data
    
    def test_player_info_has_npc_reputations(self):
        """Test that player info includes NPC reputations"""
        # Use existing player
        response = requests.get(f"{BASE_URL}/api/player/player_001")
        assert response.status_code == 200
        data = response.json()
        
        # Verify npc_reputations is a dict
        assert "npc_reputations" in data
        assert isinstance(data["npc_reputations"], dict)
    
    def test_player_info_has_rumors(self):
        """Test that player info includes rumors section"""
        response = requests.get(f"{BASE_URL}/api/player/player_001")
        assert response.status_code == 200
        data = response.json()
        
        # Verify rumors is a list
        assert "rumors" in data
        assert isinstance(data["rumors"], list)


class TestPlayersList:
    """Players list endpoint tests"""
    
    def test_get_all_players(self):
        """Test getting all players"""
        response = requests.get(f"{BASE_URL}/api/players")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "players" in data
        assert isinstance(data["players"], list)
    
    def test_players_list_structure(self):
        """Test that players list has correct structure"""
        response = requests.get(f"{BASE_URL}/api/players")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["players"]) > 0:
            player = data["players"][0]
            assert "player_id" in player
            assert "player_name" in player
            assert "total_interactions" in player
            assert "global_reputation" in player


class TestNPCRelationships:
    """NPC relationships endpoint tests"""
    
    def test_get_npc_relationships(self):
        """Test getting NPC relationships"""
        response = requests.get(f"{BASE_URL}/api/npc/relationships/vera")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "npc_id" in data
        assert data["npc_id"] == "vera"
        assert "relationships" in data
        assert isinstance(data["relationships"], list)


class TestNPCList:
    """NPC list endpoint tests"""
    
    def test_get_npc_list(self):
        """Test getting list of active NPCs"""
        response = requests.get(f"{BASE_URL}/api/npc/list")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "npcs" in data
        assert isinstance(data["npcs"], list)
    
    def test_npc_list_structure(self):
        """Test that NPC list has correct structure"""
        response = requests.get(f"{BASE_URL}/api/npc/list")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["npcs"]) > 0:
            npc = data["npcs"][0]
            assert "npc_id" in npc
            assert "role" in npc
            assert "location" in npc
            assert "mood" in npc


class TestNPCStatus:
    """NPC status endpoint tests"""
    
    def test_get_npc_status(self):
        """Test getting NPC status"""
        # First ensure vera is initialized
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        response = requests.get(f"{BASE_URL}/api/npc/status/vera")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "npc_id" in data
        assert data["npc_id"] == "vera"
        assert "active" in data
        assert "vitals" in data
        assert "emotional_state" in data
        assert "personality" in data
    
    def test_status_nonexistent_npc(self):
        """Test status for non-existent NPC returns error"""
        response = requests.get(f"{BASE_URL}/api/npc/status/nonexistent_npc_xyz")
        # Should return 404 or 520 (Cloudflare error wrapping 404)
        assert response.status_code in [404, 520]
        data = response.json()
        assert "detail" in data or "error" in data


class TestQuestEndpoints:
    """Quest-related endpoint tests"""
    
    def test_get_available_quests(self):
        """Test getting available quests"""
        response = requests.get(f"{BASE_URL}/api/quests/available")
        assert response.status_code == 200
        data = response.json()
        
        assert "quests" in data
        assert isinstance(data["quests"], list)


class TestTerritoryEndpoints:
    """Territory-related endpoint tests"""
    
    def test_get_territory_overview(self):
        """Test getting territory overview"""
        response = requests.get(f"{BASE_URL}/api/territory/overview")
        assert response.status_code == 200
        # Response should be a dict with faction data
        data = response.json()
        assert isinstance(data, dict)


class TestFactionsEndpoint:
    """Factions endpoint tests"""
    
    def test_get_factions(self):
        """Test getting factions"""
        response = requests.get(f"{BASE_URL}/api/factions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
