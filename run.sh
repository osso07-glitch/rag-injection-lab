#!/usr/bin/env bash
# Always run Streamlit with this project's .venv (avoids Anaconda/system mixups).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Creating .venv…"
  python3 -m venv "$ROOT/.venv"
fi

"$ROOT/.venv/bin/python" -m pip install -q -e ".$([ -n "${RAG_LAB_DEV:-}" ] && echo '[dev]' || true)"

# Fail fast with a clear message if core deps still missing
"$ROOT/.venv/bin/python" -c "import numpy, pandas" 2>/dev/null || {
  echo "Installing dependencies into .venv…"
  "$ROOT/.venv/bin/python" -m pip install -e ".[dev]"
}

echo "Using: $("$ROOT/.venv/bin/python" -c 'import sys; print(sys.executable)')"
echo "Starting Streamlit at http://127.0.0.1:8505"
exec "$ROOT/.venv/bin/python" -m streamlit run "$ROOT/app/Home.py" \
  --server.address 127.0.0.1 \
  --server.port 8505 \
  --browser.gatherUsageStats false
