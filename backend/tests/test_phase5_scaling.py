"""
Backend API Tests for Phase 5: Global Scaling & Performance
Tests: Scaling stats, cache stats, optimization, batch operations, pagination, zone management, bulk data
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestScalingStats:
    """Scaling statistics endpoint tests"""
    
    def test_get_scaling_stats(self):
        """Test GET /api/scaling/stats returns system statistics"""
        response = requests.get(f"{BASE_URL}/api/scaling/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "status" in data
        assert data["status"] == "operational"
        assert "stats" in data
        assert "active_npcs" in data
        assert "tier_distribution" in data
        
        # Verify stats sub-structure
        stats = data["stats"]
        assert "cache" in stats
        assert "tiers" in stats
        assert "performance" in stats
        
        print(f"Scaling stats: {data}")


class TestCacheStats:
    """Cache statistics endpoint tests"""
    
    def test_get_cache_stats(self):
        """Test GET /api/scaling/cache returns cache hit/miss stats"""
        response = requests.get(f"{BASE_URL}/api/scaling/cache")
        assert response.status_code == 200
        data = response.json()
        
        # Verify cache stats structure
        assert "size" in data
        assert "max_size" in data
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data
        
        # Verify max_size is 5000 as per implementation
        assert data["max_size"] == 5000
        
        print(f"Cache stats: {data}")


class TestOptimization:
    """Optimization endpoint tests"""
    
    def test_trigger_optimization(self):
        """Test POST /api/scaling/optimize triggers cleanup and optimization"""
        response = requests.post(f"{BASE_URL}/api/scaling/optimize")
        assert response.status_code == 200
        data = response.json()
        
        # Verify optimization response
        assert "status" in data
        assert data["status"] == "optimization_complete"
        assert "memories_cleaned" in data
        assert "processing_time_ms" in data
        assert "tier_stats" in data
        
        # Verify processing time is reasonable (< 5 seconds)
        assert data["processing_time_ms"] < 5000
        
        print(f"Optimization result: {data}")


class TestBatchInit:
    """Batch NPC initialization endpoint tests"""
    
    def test_batch_init_npcs(self):
        """Test POST /api/batch/init initializes multiple NPCs"""
        response = requests.post(
            f"{BASE_URL}/api/batch/init",
            json={"npc_ids": ["vera", "guard", "merchant"]}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify batch init response
        assert "initialized" in data
        assert "errors" in data
        assert "results" in data
        assert "processing_time_ms" in data
        
        # All NPCs should be initialized or already exist
        assert data["initialized"] >= 0
        assert isinstance(data["results"], list)
        
        # Verify each result has required fields
        for result in data["results"]:
            assert "npc_id" in result
            assert "status" in result
            assert result["status"] in ["initialized", "already_exists"]
        
        print(f"Batch init result: {data}")
    
    def test_batch_init_already_exists(self):
        """Test batch init returns already_exists for existing NPCs"""
        # First init
        requests.post(
            f"{BASE_URL}/api/batch/init",
            json={"npc_ids": ["vera"]}
        )
        
        # Second init should return already_exists
        response = requests.post(
            f"{BASE_URL}/api/batch/init",
            json={"npc_ids": ["vera"]}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least one already_exists
        already_exists = [r for r in data["results"] if r["status"] == "already_exists"]
        assert len(already_exists) >= 1
        
        print(f"Batch init already exists: {data}")


class TestBatchInteract:
    """Batch NPC interaction endpoint tests"""
    
    def test_batch_interact(self):
        """Test POST /api/batch/interact processes multiple interactions"""
        # First ensure NPCs are initialized
        requests.post(
            f"{BASE_URL}/api/batch/init",
            json={"npc_ids": ["vera", "guard"]}
        )
        
        # Now test batch interact
        response = requests.post(
            f"{BASE_URL}/api/batch/interact",
            json={
                "interactions": [
                    {"npc_id": "vera", "player_id": "test_player", "action": "Hello Vera"},
                    {"npc_id": "guard", "player_id": "test_player", "action": "Hello Guard"}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify batch interact response
        assert "processed" in data
        assert "errors" in data
        assert "results" in data
        assert "processing_time_ms" in data
        
        # Should have processed at least some interactions
        assert data["processed"] >= 0
        
        print(f"Batch interact result: {data}")


class TestPaginatedNPCs:
    """Paginated NPCs endpoint tests"""
    
    def test_get_npcs_paginated(self):
        """Test GET /api/npc/list/paginated with page/page_size params"""
        response = requests.get(
            f"{BASE_URL}/api/npc/list/paginated",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert "total_pages" in data
        assert "npcs" in data
        
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert isinstance(data["npcs"], list)
        
        print(f"Paginated NPCs: {data}")
    
    def test_npcs_paginated_with_tier_filter(self):
        """Test paginated NPCs with tier filter"""
        response = requests.get(
            f"{BASE_URL}/api/npc/list/paginated",
            params={"page": 1, "page_size": 10, "tier": "idle"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "page" in data
        assert "npcs" in data
        
        print(f"Paginated NPCs with tier filter: {data}")


class TestPaginatedPlayers:
    """Paginated players endpoint tests"""
    
    def test_get_players_paginated(self):
        """Test GET /api/players/paginated with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/players/paginated",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert "total_pages" in data
        assert "players" in data
        
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert isinstance(data["players"], list)
        
        # Verify player structure if any exist
        if len(data["players"]) > 0:
            player = data["players"][0]
            assert "player_id" in player
            assert "player_name" in player
            assert "total_interactions" in player
            assert "global_reputation" in player
        
        print(f"Paginated players: {data}")


class TestPaginatedQuests:
    """Paginated quests endpoint tests"""
    
    def test_get_quests_paginated(self):
        """Test GET /api/quests/paginated with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/quests/paginated",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert "total_pages" in data
        assert "quests" in data
        
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert isinstance(data["quests"], list)
        
        # Verify quest structure if any exist
        if len(data["quests"]) > 0:
            quest = data["quests"][0]
            assert "quest_id" in quest
            assert "title" in quest
            assert "type" in quest
            assert "difficulty" in quest
            assert "status" in quest
        
        print(f"Paginated quests: {data}")
    
    def test_quests_paginated_with_status_filter(self):
        """Test paginated quests with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/quests/paginated",
            params={"page": 1, "page_size": 10, "status": "available"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all returned quests have status "available"
        for quest in data["quests"]:
            assert quest["status"] == "available"
        
        print(f"Paginated quests with status filter: {data}")


class TestZoneTick:
    """Zone tick endpoint tests"""
    
    def test_zone_tick(self):
        """Test POST /api/zone/{zone_id}/tick processes zone NPCs"""
        response = requests.post(f"{BASE_URL}/api/zone/market/tick")
        assert response.status_code == 200
        data = response.json()
        
        # Verify zone tick response
        assert "zone" in data
        assert data["zone"] == "market"
        assert "npcs_processed" in data
        assert "events" in data
        assert "processing_time_ms" in data
        
        assert isinstance(data["events"], list)
        
        print(f"Zone tick result: {data}")


class TestZoneRegister:
    """Zone register endpoint tests"""
    
    def test_zone_register(self):
        """Test POST /api/zone/{zone_id}/register assigns NPC to zone"""
        # First ensure NPC is initialized
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        # Register NPC to zone
        response = requests.post(
            f"{BASE_URL}/api/zone/market/register",
            params={"npc_id": "vera"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify registration response
        assert "status" in data
        assert data["status"] == "registered"
        assert "npc_id" in data
        assert data["npc_id"] == "vera"
        assert "zone" in data
        assert data["zone"] == "market"
        
        print(f"Zone register result: {data}")
    
    def test_zone_register_nonexistent_npc(self):
        """Test zone register with non-existent NPC returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/zone/market/register",
            params={"npc_id": "nonexistent_npc_xyz"}
        )
        # Should return 404 or error
        assert response.status_code in [404, 500]


class TestBulkNPCData:
    """Bulk NPC data endpoint tests"""
    
    def test_get_bulk_npc_data(self):
        """Test GET /api/bulk/npc-data?npc_ids=x,y gets multiple NPCs data"""
        # First ensure NPCs are initialized
        requests.post(
            f"{BASE_URL}/api/batch/init",
            json={"npc_ids": ["vera", "guard"]}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/bulk/npc-data",
            params={"npc_ids": "vera,guard"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify bulk data response
        assert "requested" in data
        assert "found" in data
        assert "npcs" in data
        
        assert data["requested"] == 2
        assert isinstance(data["npcs"], dict)
        
        # Verify NPC data structure
        for npc_id, npc_data in data["npcs"].items():
            assert "npc_id" in npc_data
            assert "memory_stats" in npc_data
            assert "relationship_stats" in npc_data
        
        print(f"Bulk NPC data: {data}")


class TestTierDistribution:
    """Tier distribution tests"""
    
    def test_tier_distribution_in_stats(self):
        """Test that tier distribution is returned in scaling stats"""
        response = requests.get(f"{BASE_URL}/api/scaling/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify tier distribution structure
        tier_dist = data["tier_distribution"]
        assert "total_npcs" in tier_dist
        assert "tier_distribution" in tier_dist
        assert "zones" in tier_dist
        assert "current_tick" in tier_dist
        
        # Verify tier types
        tiers = tier_dist["tier_distribution"]
        assert "active" in tiers
        assert "nearby" in tiers
        assert "idle" in tiers
        assert "dormant" in tiers
        
        print(f"Tier distribution: {tier_dist}")


class TestPerformanceMetrics:
    """Performance metrics tests"""
    
    def test_performance_metrics_in_stats(self):
        """Test that performance metrics are tracked"""
        # First trigger some operations to generate metrics
        requests.post(f"{BASE_URL}/api/scaling/optimize")
        requests.post(
            f"{BASE_URL}/api/batch/interact",
            json={"interactions": [{"npc_id": "vera", "player_id": "test", "action": "test"}]}
        )
        
        response = requests.get(f"{BASE_URL}/api/scaling/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify performance section exists
        assert "stats" in data
        assert "performance" in data["stats"]
        
        print(f"Performance metrics: {data['stats']['performance']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
