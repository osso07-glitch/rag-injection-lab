"""Runtime paths and app settings. No Streamlit imports here."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: .../rag-injection-lab (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from project root if present (no-op when missing)
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default.resolve()


DATA_DIR = _env_path("RAG_LAB_DATA_DIR", PROJECT_ROOT / "data")
META_DIR = _env_path("RAG_LAB_META_DIR", PROJECT_ROOT / "meta")

KB_DIR = DATA_DIR / "kb"
KB_CLEAN_DIR = KB_DIR / "clean"
KB_POISONED_DIR = KB_DIR / "poisoned"
CORPORA_DIR = DATA_DIR / "corpora"
FINDINGS_DIR = DATA_DIR / "findings"
UPLOADS_DIR = DATA_DIR / "_uploads"
SAMPLES_DIR = DATA_DIR / "samples"
DB_PATH = META_DIR / "app.db"

MAX_UPLOAD_MB = float(os.environ.get("RAG_LAB_MAX_UPLOAD_MB", "25"))

# Streamlit / server
APP_HOST = os.environ.get("RAG_LAB_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("RAG_LAB_PORT", "8505"))

# RAG defaults
PROVIDER = os.environ.get("RAG_LAB_PROVIDER", "openai").strip().lower()  # openai|anthropic|mock
CHAT_MODEL = os.environ.get("RAG_LAB_CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.environ.get("RAG_LAB_EMBED_MODEL", "text-embedding-3-small")
TOP_K = int(os.environ.get("RAG_LAB_TOP_K", "4"))
CHUNK_SIZE = int(os.environ.get("RAG_LAB_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("RAG_LAB_CHUNK_OVERLAP", "120"))

# Feature flags (phases)
ENABLE_DETECTION = os.environ.get("RAG_LAB_ENABLE_DETECTION", "0") == "1"
ENABLE_MITIGATION = os.environ.get("RAG_LAB_ENABLE_MITIGATION", "0") == "1"


def ensure_runtime_dirs() -> None:
    """Create data and meta directories if missing; init SQLite schema when possible."""
    for path in (
        KB_CLEAN_DIR,
        KB_POISONED_DIR,
        CORPORA_DIR,
        FINDINGS_DIR,
        UPLOADS_DIR,
        SAMPLES_DIR,
        META_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
    try:
        from rag_injection_lab.meta.db import init_db

        init_db()
    except Exception:  # noqa: BLE001 — keep UI boot resilient
        pass
