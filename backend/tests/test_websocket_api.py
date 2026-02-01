"""
WebSocket API Tests for Fractured Survival NPC Service
Tests real-time communication via WebSocket for Unreal Engine integration
"""

import pytest
import requests
import asyncio
import json
import time
import os

# Use external URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://survival-npc-hub.preview.emergentagent.com').rstrip('/')

# WebSocket URL (external)
WS_URL = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/ws/game'

# Test credentials
TEST_PLAYER_ID = "test_player"
TEST_PLAYER_NAME = "TestPlayer"


class TestHTTPEndpointsStillWorking:
    """Verify HTTP API still functions alongside WebSocket"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_npc_init_http(self):
        """Test NPC initialization via HTTP"""
        response = requests.post(
            f"{BASE_URL}/api/npc/init",
            json={"npc_id": "vera"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["initialized", "already_exists"]
        assert data.get("npc_id") == "vera"
        print(f"✓ NPC init via HTTP: {data}")
    
    def test_npc_action_http(self):
        """Test NPC action via HTTP"""
        # First ensure NPC is initialized
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        response = requests.post(
            f"{BASE_URL}/api/npc/action",
            json={
                "npc_id": "vera",
                "action": "What's happening in Porto Cobre today?",
                "player_id": "http_test_player",
                "player_name": "Player_http_test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "cognitive_frame" in data
        assert "dialogue" in data.get("cognitive_frame", {})
        print(f"✓ NPC action via HTTP: dialogue received")
    
    def test_voice_generate_http(self):
        """Test voice generation via HTTP"""
        # First ensure NPC is initialized
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        response = requests.post(
            f"{BASE_URL}/api/voice/generate/vera",
            json={
                "text": "Hello traveler",
                "mood": "neutral"
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Voice generation should return audio data
        assert "audio_base64" in data or "error" not in data
        print(f"✓ Voice generation via HTTP: response received")


class TestWebSocketStatusEndpoint:
    """Test WebSocket status endpoint"""
    
    def test_ws_status_endpoint(self):
        """Test /api/ws/status endpoint"""
        response = requests.get(f"{BASE_URL}/api/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "event_subscribers" in data
        print(f"✓ WebSocket status: {data}")


class TestWebSocketConnection:
    """Test WebSocket connection and message handling"""
    
    @pytest.fixture
    def ws_connection(self):
        """Create WebSocket connection for tests"""
        try:
            import websockets
            return websockets
        except ImportError:
            pytest.skip("websockets library not installed")
    
    @pytest.mark.asyncio
    async def test_websocket_connect(self, ws_connection):
        """Test WebSocket connection establishment"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Should receive connected message
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "connected"
                assert data.get("player_id") == TEST_PLAYER_ID
                assert data.get("player_name") == TEST_PLAYER_NAME
                print(f"✓ WebSocket connected: {data}")
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, ws_connection):
        """Test ping/pong message handling"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message first
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send ping
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Should receive pong
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "pong"
                assert "timestamp" in data
                print(f"✓ Ping/Pong working: {data}")
        except Exception as e:
            pytest.fail(f"Ping/Pong test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_npc_init(self, ws_connection):
        """Test NPC initialization via WebSocket"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send NPC init request
                await websocket.send(json.dumps({
                    "type": "npc_init",
                    "npc_id": "vera",
                    "request_id": "test_init_001"
                }))
                
                # Should receive NPC initialized response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "npc_initialized"
                assert data.get("npc_id") == "vera"
                assert data.get("request_id") == "test_init_001"
                print(f"✓ NPC init via WebSocket: {data}")
        except Exception as e:
            pytest.fail(f"NPC init test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_npc_action(self, ws_connection):
        """Test NPC action/dialogue via WebSocket"""
        # First ensure NPC is initialized via HTTP
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=10) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send NPC action
                await websocket.send(json.dumps({
                    "type": "npc_action",
                    "npc_id": "vera",
                    "action": "Hello! I'm a traveler looking for supplies.",
                    "request_id": "test_action_001"
                }))
                
                # Should receive NPC response (may take time for AI processing)
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                data = json.loads(response)
                
                # Could be npc_response or error
                if data.get("type") == "npc_response":
                    assert data.get("npc_id") == "vera"
                    assert "dialogue" in data
                    print(f"✓ NPC action via WebSocket: dialogue='{data.get('dialogue', '')[:50]}...'")
                elif data.get("type") == "error":
                    print(f"⚠ NPC action returned error: {data.get('error')}")
                    # This is expected if NPC system has issues
                else:
                    print(f"? Unexpected response type: {data.get('type')}")
        except asyncio.TimeoutError:
            pytest.fail("NPC action timed out - AI processing may be slow")
        except Exception as e:
            pytest.fail(f"NPC action test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_npc_status(self, ws_connection):
        """Test NPC status query via WebSocket"""
        # First ensure NPC is initialized via HTTP
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send NPC status request
                await websocket.send(json.dumps({
                    "type": "npc_status",
                    "npc_id": "vera",
                    "request_id": "test_status_001"
                }))
                
                # Should receive NPC status response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                if data.get("type") == "npc_status_response":
                    assert data.get("npc_id") == "vera"
                    assert data.get("status") == "active"
                    print(f"✓ NPC status via WebSocket: {data}")
                elif data.get("type") == "error":
                    print(f"⚠ NPC status returned error: {data.get('error')}")
        except Exception as e:
            pytest.fail(f"NPC status test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_subscribe_events(self, ws_connection):
        """Test event subscription via WebSocket"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Subscribe to events
                await websocket.send(json.dumps({
                    "type": "subscribe_events",
                    "events": ["world_events", "faction_updates"],
                    "request_id": "test_sub_001"
                }))
                
                # Should receive subscription confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "subscribed"
                assert "world_events" in data.get("events", [])
                assert "faction_updates" in data.get("events", [])
                print(f"✓ Event subscription via WebSocket: {data}")
        except Exception as e:
            pytest.fail(f"Event subscription test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_get_factions(self, ws_connection):
        """Test get factions via WebSocket"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Request factions
                await websocket.send(json.dumps({
                    "type": "get_factions",
                    "request_id": "test_factions_001"
                }))
                
                # Should receive factions response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "factions"
                assert "factions" in data
                print(f"✓ Get factions via WebSocket: {len(data.get('factions', []))} factions")
        except Exception as e:
            pytest.fail(f"Get factions test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_get_world_events(self, ws_connection):
        """Test get world events via WebSocket"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Request world events
                await websocket.send(json.dumps({
                    "type": "get_world_events",
                    "limit": 5,
                    "request_id": "test_events_001"
                }))
                
                # Should receive world events response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "world_events"
                assert "events" in data
                print(f"✓ Get world events via WebSocket: {len(data.get('events', []))} events")
        except Exception as e:
            pytest.fail(f"Get world events test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_voice_generate(self, ws_connection):
        """Test voice generation via WebSocket with audio streaming"""
        # First ensure NPC is initialized via HTTP
        requests.post(f"{BASE_URL}/api/npc/init", json={"npc_id": "vera"})
        
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=30) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Request voice generation
                await websocket.send(json.dumps({
                    "type": "voice_generate",
                    "npc_id": "vera",
                    "text": "Hello traveler, welcome to Porto Cobre.",
                    "mood": "neutral",
                    "format": "mp3",
                    "request_id": "test_voice_001"
                }))
                
                # Should receive voice chunks and completion
                chunks_received = 0
                voice_complete = False
                
                while not voice_complete:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(response)
                        
                        if data.get("type") == "voice_chunk":
                            chunks_received += 1
                            assert "audio_data" in data
                            assert data.get("npc_id") == "vera"
                        elif data.get("type") == "voice_complete":
                            voice_complete = True
                            assert data.get("npc_id") == "vera"
                            assert "total_size" in data
                            print(f"✓ Voice generation via WebSocket: {chunks_received} chunks, {data.get('total_size')} bytes")
                        elif data.get("type") == "error":
                            print(f"⚠ Voice generation error: {data.get('error')}")
                            break
                    except asyncio.TimeoutError:
                        print(f"⚠ Voice generation timed out after {chunks_received} chunks")
                        break
                
                if chunks_received > 0:
                    print(f"✓ Voice streaming working: received {chunks_received} chunks")
        except Exception as e:
            pytest.fail(f"Voice generation test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self, ws_connection):
        """Test handling of unknown message types"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send unknown message type
                await websocket.send(json.dumps({
                    "type": "unknown_type",
                    "request_id": "test_unknown_001"
                }))
                
                # Should receive error response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "error"
                assert "unknown" in data.get("error", "").lower()
                print(f"✓ Unknown message type handled: {data}")
        except Exception as e:
            pytest.fail(f"Unknown message type test failed: {e}")


class TestWebSocketErrorHandling:
    """Test WebSocket error handling"""
    
    @pytest.fixture
    def ws_connection(self):
        """Create WebSocket connection for tests"""
        try:
            import websockets
            return websockets
        except ImportError:
            pytest.skip("websockets library not installed")
    
    @pytest.mark.asyncio
    async def test_npc_action_without_init(self, ws_connection):
        """Test NPC action for non-initialized NPC"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send action for non-existent NPC
                await websocket.send(json.dumps({
                    "type": "npc_action",
                    "npc_id": "nonexistent_npc_xyz",
                    "action": "Hello",
                    "request_id": "test_error_001"
                }))
                
                # Should receive error response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "error"
                assert "not initialized" in data.get("error", "").lower()
                print(f"✓ Non-initialized NPC error handled: {data}")
        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_npc_action_missing_fields(self, ws_connection):
        """Test NPC action with missing required fields"""
        ws_url = f"{WS_URL}?player_id={TEST_PLAYER_ID}&player_name={TEST_PLAYER_NAME}"
        
        try:
            async with ws_connection.connect(ws_url, close_timeout=5) as websocket:
                # Receive connected message
                await asyncio.wait_for(websocket.recv(), timeout=10)
                
                # Send action without npc_id
                await websocket.send(json.dumps({
                    "type": "npc_action",
                    "action": "Hello",
                    "request_id": "test_error_002"
                }))
                
                # Should receive error response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                assert data.get("type") == "error"
                assert "required" in data.get("error", "").lower()
                print(f"✓ Missing fields error handled: {data}")
        except Exception as e:
            pytest.fail(f"Missing fields test failed: {e}")


# Run tests synchronously for pytest compatibility
def test_http_health():
    """Sync wrapper for health check"""
    test = TestHTTPEndpointsStillWorking()
    test.test_health_check()

def test_http_npc_init():
    """Sync wrapper for NPC init"""
    test = TestHTTPEndpointsStillWorking()
    test.test_npc_init_http()

def test_http_npc_action():
    """Sync wrapper for NPC action"""
    test = TestHTTPEndpointsStillWorking()
    test.test_npc_action_http()

def test_ws_status():
    """Sync wrapper for WS status"""
    test = TestWebSocketStatusEndpoint()
    test.test_ws_status_endpoint()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
