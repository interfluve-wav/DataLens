#!/usr/bin/env bash
# Start DataLens API (uvicorn) then React frontend (Vite).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_python() {
  if [[ -x "$ROOT/venv/bin/python3.14" ]]; then
    echo "$ROOT/venv/bin/python3.14"
  elif [[ -x "$ROOT/venv/bin/python3" ]]; then
    echo "$ROOT/venv/bin/python3"
  elif [[ -x "$ROOT/.venv/bin/python3" ]]; then
    echo "$ROOT/.venv/bin/python3"
  else
    echo "python3"
  fi
}

PYTHON="$(pick_python)"

if ! "$PYTHON" -c "import uvicorn, fastapi" 2>/dev/null; then
  echo "Missing Python deps. Create a venv and run: pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT/frontend" && npm install)
fi

cleanup() {
  echo ""
  echo "Stopping DataLens..."
  if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
  if [[ -n "${FE_PID:-}" ]]; then kill "$FE_PID" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API (http://127.0.0.1:8000)..."
"$PYTHON" -m uvicorn api:app --reload --port 8000 &
API_PID=$!

echo -n "Waiting for API"
for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
    echo " — ready"
    break
  fi
  echo -n "."
  sleep 0.25
done

if ! curl -sf "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
  echo ""
  echo "API did not become ready on port 8000. Check logs above."
  exit 1
fi

echo "Starting frontend (http://localhost:5173)..."
(cd "$ROOT/frontend" && npm run dev) &
FE_PID=$!

echo ""
echo "DataLens dev stack running:"
echo "  Frontend  http://localhost:5173"
echo "  API       http://127.0.0.1:8000"
echo "  Health    http://127.0.0.1:8000/api/health"
echo ""
echo "Press Ctrl+C to stop both."

wait
