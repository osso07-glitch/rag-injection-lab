#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Creating .venv…"
  python3 -m venv "$ROOT/.venv"
fi

"$ROOT/.venv/bin/python" -m pip install -q -e ".$([ -n "${RAG_LAB_DEV:-}" ] && echo '[dev]' || true)"

"$ROOT/.venv/bin/python" -c "import numpy, pandas" 2>/dev/null || {
  echo "Installing dependencies into .venv…"
  "$ROOT/.venv/bin/python" -m pip install -e ".[dev]"
}

HOST="${RAG_LAB_HOST:-127.0.0.1}"
PORT="${RAG_LAB_PORT:-8505}"
echo "Using: $("$ROOT/.venv/bin/python" -c 'import sys; print(sys.executable)')"
echo "Starting Streamlit at http://${HOST}:${PORT}"
exec "$ROOT/.venv/bin/python" -m streamlit run "$ROOT/app/Home.py" \
  --server.address "$HOST" \
  --server.port "$PORT" \
  --browser.gatherUsageStats false
