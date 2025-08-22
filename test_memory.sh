#!/bin/bash
# Test script to verify memory questions work correctly

echo "🧪 Testing Memory Questions with Session Persistence"
echo "=================================================="

# Use cookies to maintain session
COOKIES_FILE="test_cookies.txt"

echo "🔹 Step 1: Ask first question"
curl -c $COOKIES_FILE -b $COOKIES_FILE -s -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I open an account?"}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Response: {data[\"response\"][:100]}...')
print(f'📊 Session ID: {data.get(\"session_id\", \"None\")}')
print(f'🔢 Session Questions: {data.get(\"session_debug\", {}).get(\"current_session_questions\", \"Unknown\")}')
print(f'🎯 Analysis: {data.get(\"analysis\", {}).get(\"handling_strategy\", \"Unknown\")}')
print()
"

echo "🔹 Step 2: Ask memory question (should show 2 questions)"
curl -c $COOKIES_FILE -b $COOKIES_FILE -s -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many questions did I ask?"}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Response: {data[\"response\"]}')
print(f'📊 Session ID: {data.get(\"session_id\", \"None\")}')
print(f'🔢 Session Questions: {data.get(\"session_debug\", {}).get(\"current_session_questions\", \"Unknown\")}')
print(f'🎯 Analysis: {data.get(\"analysis\", {}).get(\"handling_strategy\", \"Unknown\")}')
print(f'🧠 Message Type: {data.get(\"analysis\", {}).get(\"message_type\", \"Unknown\")}')
print()
"

echo "🔹 Step 3: Ask about first question"
curl -c $COOKIES_FILE -b $COOKIES_FILE -s -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What was my first question?"}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Response: {data[\"response\"]}')
print(f'📊 Session ID: {data.get(\"session_id\", \"None\")}')
print(f'🔢 Session Questions: {data.get(\"session_debug\", {}).get(\"current_session_questions\", \"Unknown\")}')
print(f'🎯 Analysis: {data.get(\"analysis\", {}).get(\"handling_strategy\", \"Unknown\")}')
print()
"

echo "🔹 Step 4: Ask final memory question (should show 4 questions)"
curl -c $COOKIES_FILE -b $COOKIES_FILE -s -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How many questions have I asked now?"}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'✅ Response: {data[\"response\"]}')
print(f'📊 Session ID: {data.get(\"session_id\", \"None\")}')
print(f'🔢 Session Questions: {data.get(\"session_debug\", {}).get(\"current_session_questions\", \"Unknown\")}')
print(f'🎯 Analysis: {data.get(\"analysis\", {}).get(\"handling_strategy\", \"Unknown\")}')
print()
"

# Clean up
rm -f $COOKIES_FILE

echo "✅ Test completed!"
echo ""
echo "🎯 Expected Results:"
echo "   - Same session ID across all requests"
echo "   - Question count: 1, 2, 3, 4"
echo "   - Memory questions use 'memory_analysis' strategy"
echo "   - Should remember first question was 'How do I open an account?'"