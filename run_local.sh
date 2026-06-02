#!/usr/bin/env bash
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
# run_local.sh  â  Start the full Geopolitical Risk Intelligence stack locally
#
#  Starts three processes in separate terminals (or background jobs):
#    1) CAP backend   â http://localhost:4004
#    2) React UI      â http://localhost:5173   (hot-reload dev server)
#    3) Python agent  â http://localhost:5000   (A2A endpoint)
#
#  Prerequisites: Node.js + npm, Python 3.10+, and all dependencies installed.
#  No BTP credentials needed â IBD_TESTING=1 uses mocked SAP data.
# âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAP_DIR="$SCRIPT_DIR/assets/geopolitical-risk-cap"
AGENT_DIR="$SCRIPT_DIR/assets/geopolitical-risk-agent"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${GREEN}[run_local]${NC} $1"; }
warn() { echo -e "${YELLOW}[run_local]${NC} $1"; }

# ââ 1. CAP backend ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
log "Starting CAP backend on http://localhost:4004 ..."
cd "$CAP_DIR"
(npm run watch 2>&1 | sed 's/^/[CAP] /' &)
CAP_PID=$!

# ââ 2. React UI dev server ââââââââââââââââââââââââââââââââââââââââââââââââââââ
log "Starting React UI on http://localhost:5173 ..."
cd "$CAP_DIR/ui"
(npm run dev 2>&1 | sed 's/^/[UI]  /' &)
UI_PID=$!

# ââ 3. Python agent âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
log "Starting agent on http://localhost:5000 ..."
cd "$AGENT_DIR"
(IBD_TESTING=1 python3 app/main.py 2>&1 | sed 's/^/[AGT] /' &)
AGENT_PID=$!

# ââ Wait a moment, then show access URLs âââââââââââââââââââââââââââââââââââââ
sleep 4
echo ""
echo -e "${GREEN}ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ${NC}"
echo -e "${GREEN}  ð Geopolitical Risk Intelligence Agent â LOCAL DEV MODE  ${NC}"
echo -e "${GREEN}ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ${NC}"
echo -e "  Dashboard (React)  â  ${YELLOW}http://localhost:5173${NC}"
echo -e "  CAP OData service  â  ${YELLOW}http://localhost:4004/risk${NC}"
echo -e "  Agent A2A          â  ${YELLOW}http://localhost:5000${NC}"
echo -e "  Architecture view  â  ${YELLOW}http://localhost:4004/flowchart.html${NC}"
echo ""
echo -e "  Trigger a manual scan:  ${YELLOW}./trigger_scan.sh${NC}"
echo -e "  Press Ctrl+C to stop all services."
echo -e "${GREEN}ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ${NC}"
echo ""

# Keep script running; kill children on exit
trap "kill $CAP_PID $UI_PID $AGENT_PID 2>/dev/null; echo ''; log 'All services stopped.'" INT TERM
wait
