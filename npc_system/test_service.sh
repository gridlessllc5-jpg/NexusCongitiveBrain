#!/bin/bash
# Test the standalone NPC service

echo "======================================================================"
echo "Testing Standalone NPC Service"
echo "======================================================================"
echo ""

# Health check
echo "1. Health Check..."
curl -s http://localhost:9000/ | python3 -m json.tool
echo ""

# Initialize Vera
echo "2. Initializing Vera..."
curl -s -X POST http://localhost:9000/npc/init \
  -H "Content-Type: application/json" \
  -d '{"npc_id": "vera"}' | python3 -m json.tool
echo ""

sleep 2

# Send action
echo "3. Sending player action..."
curl -s -X POST http://localhost:9000/npc/action \
  -H "Content-Type: application/json" \
  -d '{"npc_id": "vera", "action": "I approach slowly with my hands raised"}' | python3 -m json.tool | head -30
echo ""

# Get status
echo "4. Getting NPC status..."
curl -s http://localhost:9000/npc/status/vera | python3 -m json.tool
echo ""

# List NPCs
echo "5. Listing active NPCs..."
curl -s http://localhost:9000/npc/list | python3 -m json.tool
echo ""

echo "======================================================================"
echo "Test Complete!"
echo "======================================================================"
