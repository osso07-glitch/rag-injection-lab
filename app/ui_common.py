"""Shared Streamlit chrome. Keep logic thin — services live in the package."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

__all__ = [
    "init_app",
    "page_header",
    "require_corpus",
    "set_active_corpus",
]

# Ensure `src/` is importable when running `streamlit run app/Home.py` without install.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _missing_dep_page(missing: str) -> None:
    st.set_page_config(page_title="RAG Injection Lab — setup", page_icon="🧪")
    st.error(f"Missing dependency: **{missing}**")
    st.code(sys.executable, language="text")
    st.markdown(
        """
Streamlit is using the Python above, which does not have the package installed
(common when **Anaconda**, system Python, and a project `.venv` get mixed).

### Recommended fix

```bash
cd /path/to/rag-injection-lab
chmod +x run.sh
./run.sh
```

### Or install into *this* interpreter

```bash
python -m pip install -e ".[dev]"
python -m streamlit run app/Home.py
```

Stop the old Streamlit process (Ctrl+C) before restarting.
"""
    )
    st.stop()


try:
    import numpy as _numpy  # noqa: F401
    import pandas as _pandas  # noqa: F401
    from rag_injection_lab import __version__
    from rag_injection_lab.config import ensure_runtime_dirs
except ModuleNotFoundError as exc:
    _missing_dep_page(getattr(exc, "name", None) or str(exc))


def init_app() -> None:
    """Page config + runtime dirs + session defaults. Call once per page."""
    st.set_page_config(
        page_title="RAG Injection Lab",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ensure_runtime_dirs()
    _ensure_session_defaults()
    _render_sidebar()


def _ensure_session_defaults() -> None:
    defaults: dict[str, Any] = {
        "corpus_id": None,
        "corpus_meta": None,
        "ingest_report": None,
        "last_query": None,
        "provider": "mock",
        "mitigation": "none",
        "run_detection": True,
        "include_poisoned": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_active_corpus(corpus_meta: dict[str, Any], ingest_report: dict[str, Any] | None = None) -> None:
    st.session_state.corpus_id = corpus_meta.get("corpus_id")
    st.session_state.corpus_meta = corpus_meta
    st.session_state.ingest_report = ingest_report


def require_corpus() -> str:
    cid = st.session_state.get("corpus_id")
    if not cid:
        st.warning("No corpus loaded yet.")
        st.page_link("pages/1_Knowledge_Base.py", label="Build or select a corpus", icon="📚")
        st.stop()
    return str(cid)


def page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(f"**RAG Injection Lab** `v{__version__}`")
        cid = st.session_state.get("corpus_id")
        meta = st.session_state.get("corpus_meta") or {}
        if cid:
            st.success(f"Corpus: `{cid}`")
            st.caption(
                f"{meta.get('n_docs', '?')} docs · {meta.get('n_chunks', '?')} chunks · "
                f"{meta.get('embed_model', '?')}"
            )
        else:
            st.info("No corpus active")
        st.divider()
        st.caption("Local only · **127.0.0.1:8505** · no auth")
        st.caption("Design: `docs/design.md`")
