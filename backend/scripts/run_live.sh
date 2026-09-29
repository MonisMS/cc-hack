#!/usr/bin/env bash
# Run the live backend: API + worker + ngrok tunnel on the fixed domain.
# Ctrl+C stops all three. Logs go to backend/logs/.
#
#   cd backend && ./scripts/run_live.sh
#
# Override the tunnel domain with NGROK_DOMAIN=... if the ngrok account changes.
set -euo pipefail

NGROK_DOMAIN="${NGROK_DOMAIN:-stingray-stirring-carefully.ngrok-free.app}"
cd "$(dirname "$0")/.."
mkdir -p logs

pids=()
cleanup() {
  echo "Stopping..."
  kill "${pids[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 >> logs/api.log 2>&1 &
pids+=($!)
uv run python -m app.worker >> logs/worker.log 2>&1 &
pids+=($!)
ngrok http --url="$NGROK_DOMAIN" 8000 --log=stdout >> logs/ngrok.log 2>&1 &
pids+=($!)

echo "Waiting for the API to load the CLIP models..."
for _ in $(seq 1 90); do
  if curl -sf -H "ngrok-skip-browser-warning: 1" "https://$NGROK_DOMAIN/health" > /dev/null; then
    echo "LIVE: https://$NGROK_DOMAIN  (logs in backend/logs/, Ctrl+C to stop)"
    wait -n
    echo "A process exited; check backend/logs/. Stopping the rest."
    exit 1
  fi
  sleep 2
done
echo "API did not come up within 3 minutes; check backend/logs/api.log"
exit 1
