#!/usr/bin/env bash
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# trigger_scan.sh  â  Fire a manual risk scan against the local agent
#
#  Usage:
#    ./trigger_scan.sh              â default scan (all configured regions)
#    ./trigger_scan.sh "Ukraine"    â focus query
#
#  Requires the agent to be running on http://localhost:5000
#  (start with run_local.sh or:  cd assets/geopolitical-risk-agent && python3 app/main.py)
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
set -e

AGENT_URL="${AGENT_URL:-http://localhost:5000}"
QUERY="${1:-run geopolitical risk scan for all monitored regions}"
TASK_ID="task-$(date +%s)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${GREEN}[trigger]${NC} Sending scan request to $AGENT_URL ..."
echo -e "${GREEN}[trigger]${NC} Query: \"$QUERY\""
echo ""

PAYLOAD=$(cat <<JSON
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tasks/send",
  "params": {
    "id": "$TASK_ID",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "$QUERY"}]
    }
  }
}
JSON
)

RESPONSE=$(curl -s -X POST "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Poll for result (up to 120 seconds)
echo -e "${GREEN}[trigger]${NC} Polling for result (timeout 120s) ..."
for i in $(seq 1 24); do
  sleep 5
  STATUS_PAYLOAD=$(cat <<JSON
{
  "jsonrpc": "2.0",
  "id": $i,
  "method": "tasks/get",
  "params": {"id": "$TASK_ID"}
}
JSON
)
  STATUS=$(curl -s -X POST "$AGENT_URL" \
    -H "Content-Type: application/json" \
    -d "$STATUS_PAYLOAD")

  STATE=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('status',{}).get('state','unknown'))" 2>/dev/null || echo "unknown")
  echo -e "${YELLOW}[trigger]${NC} Attempt $i/24 â state: $STATE"

  if [[ "$STATE" == "completed" || "$STATE" == "failed" ]]; then
    echo ""
    echo -e "${GREEN}[trigger]${NC} Final result:"
    echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"
    break
  fi
done

echo ""
echo -e "${GREEN}[trigger]${NC} Done. Open http://localhost:5173 to see results in the dashboard."
