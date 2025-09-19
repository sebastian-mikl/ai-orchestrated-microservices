#!/bin/bash

# Test script for Service Registry

echo "Testing Service Registry RAG Orchestration"
echo "=========================================="

BASE_URL="http://localhost:8004"

echo ""
echo "1. Health Check"
curl -s $BASE_URL/health | jq '.'

echo ""
echo "2. List Registered Services"
curl -s $BASE_URL/services | jq '.count, .services | keys'

echo ""
echo "3. Search for text transformation services"
curl -s "$BASE_URL/services/search/transform%20text%20uppercase" | jq '.'

echo ""
echo "4. Search for storage services"
curl -s "$BASE_URL/services/search/save%20data%20store" | jq '.'

echo ""
echo "5. Generate orchestration for 'make text uppercase and save it'"
curl -s -X POST $BASE_URL/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"command": "make text uppercase and save it", "data": "hello world"}' | jq '.'

echo ""
echo "6. Execute full orchestration chain"
curl -s -X POST $BASE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "transform this text to uppercase and store it", "data": "test message from registry"}' | jq '.'

echo ""
echo "7. Test natural language command"
curl -s -X POST $BASE_URL/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "I want to save some text after making it all caps", "data": "this should become uppercase"}' | jq '.'

echo ""
echo "8. Check storage contents"
curl -s http://localhost:8003/storage/list | jq '.'

echo ""
echo "=========================================="
echo "Test complete!"