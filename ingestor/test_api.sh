#!/bin/bash

# =============================================================================
# EXPERT SEARCH API TEST SCRIPT
# =============================================================================

BASE_URL="http://localhost:8001"

echo "🧪 Testing Expert Search API Endpoints"
echo "========================================"

# Function to make a GET request and show result
test_get() {
    echo "📡 GET $1"
    curl -s -X GET "$BASE_URL$1" | jq -C '.' 2>/dev/null || curl -s -X GET "$BASE_URL$1"
    echo ""
}

# Function to make a POST request and show result
test_post() {
    echo "📡 POST $1"
    echo "📄 Body: $2"
    curl -s -X POST "$BASE_URL$1" \
        -H "Content-Type: application/json" \
        -d "$2" | jq -C '.' 2>/dev/null || curl -s -X POST "$BASE_URL$1" -H "Content-Type: application/json" -d "$2"
    echo ""
}

echo "🔍 1. Testing basic skill search..."
test_get "/experts/skill/php"

echo "🔍 2. Testing skill search with parameters..."
test_get "/experts/skill/php?min_confidence=0.5&limit=3"

echo "🔍 3. Testing natural language search..."
test_post "/experts/search" '{"query": "php", "min_confidence": 0.3}'

echo "🔍 4. Testing fuzzy search..."
test_post "/experts/search" '{"query": "reac"}'

echo "🔍 5. Testing multi-skill search (OR)..."
test_post "/experts/skills" '{"skills": ["php", "python"], "operator": "OR"}'

echo "🔍 6. Testing skill suggestions..."
test_get "/skills/suggest?q=pyt&limit=5"

echo "📊 7. Testing system status..."
test_get "/"

echo "📊 8. Testing queue stats..."
test_get "/queue/stats"

echo "✅ API testing completed!"
echo ""
echo "💡 To run individual tests, use the curl commands from the output above"
echo "💡 Add '| jq' to any curl command for pretty JSON formatting"
