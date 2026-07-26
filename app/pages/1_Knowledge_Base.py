"""Knowledge Base — ingest clean/poisoned docs into a corpus."""

from __future__ import annotations

import importlib
from pathlib import Path

import streamlit as st

import ui_common as _ui_common

importlib.reload(_ui_common)
from ui_common import init_app, page_header, set_active_corpus  # noqa: E402

from rag_injection_lab.config import PROVIDER, UPLOADS_DIR
from rag_injection_lab.services.corpus_service import get_chunk_preview, get_corpora
from rag_injection_lab.services.ingest_service import (
    build_corpus,
    list_clean_kb,
    list_poisoned_kb,
    store_upload,
)

init_app()
page_header("Knowledge Base", "Ingest policy docs → chunk → embed → corpus on disk")

clean = list_clean_kb()
poisoned = list_poisoned_kb()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Clean KB")
    if clean:
        for p in clean:
            st.markdown(f"- `{p.name}`")
    else:
        st.info("No files in `data/kb/clean/`")
with col_b:
    st.subheader("Poisoned KB (lab)")
    if poisoned:
        for p in poisoned:
            st.markdown(f"- `{p.name}`")
    else:
        st.caption("No poisoned docs yet.")

st.divider()
st.subheader("Build corpus")

name = st.text_input("Corpus name", value="acme-clean")
include_clean = st.checkbox("Include clean KB", value=True)
include_poisoned = st.checkbox(
    "Include poisoned KB",
    value=False,
    help="Phase 1: plant injection payloads into retrieval.",
)
provider = st.selectbox(
    "Embedding / LLM provider family",
    options=["mock", "openai", "anthropic"],
    index=["mock", "openai", "anthropic"].index(PROVIDER)
    if PROVIDER in ("mock", "openai", "anthropic")
    else 0,
    help="mock = offline hash embeddings + echo generator (no API key).",
)
st.session_state.provider = provider

uploaded = st.file_uploader(
    "Optional extra documents",
    type=["txt", "md", "pdf"],
    accept_multiple_files=True,
)
extra_paths: list[Path] = []
if uploaded:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for f in uploaded:
        dest = UPLOADS_DIR / f.name
        dest.write_bytes(f.getvalue())
        extra_paths.append(dest)
        st.caption(f"Saved upload `{dest.name}`")

if st.button("Build corpus", type="primary"):
    try:
        with st.spinner("Chunking and embedding…"):
            report = build_corpus(
                name=name,
                include_clean=include_clean,
                include_poisoned=include_poisoned,
                extra_paths=extra_paths or None,
                provider=provider,
            )
        meta = {
            "corpus_id": report.corpus_id,
            "name": name,
            "n_docs": report.n_docs,
            "n_chunks": report.n_chunks,
            "embed_model": report.embed_model,
            "provider": report.provider,
            "include_poisoned": include_poisoned,
            "created_at": report.created_at,
        }
        set_active_corpus(meta, report.to_dict())
        st.session_state.include_poisoned = include_poisoned
        st.success(
            f"Built **{report.corpus_id}** — {report.n_docs} docs, {report.n_chunks} chunks "
            f"({report.embed_model})"
        )
        for w in report.warnings:
            st.warning(w)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))

st.divider()
st.subheader("Existing corpora")
corpora = get_corpora()
if not corpora:
    st.caption("None yet — build one above.")
else:
    labels = {
        f"{c.corpus_id}  ({c.n_docs} docs, {c.n_chunks} chunks, {c.embed_model})": c
        for c in corpora
    }
    choice = st.selectbox("Select corpus", list(labels.keys()))
    if choice and st.button("Activate selected"):
        c = labels[choice]
        set_active_corpus(c.to_dict())
        st.success(f"Active: `{c.corpus_id}`")
        st.rerun()

    if st.session_state.get("corpus_id"):
        st.subheader("Chunk preview")
        try:
            preview = get_chunk_preview(st.session_state.corpus_id, limit=15)
            import pandas as pd

            df = pd.DataFrame(preview)
            if not df.empty:
                show = df[["chunk_id", "doc_name", "kind", "index"]].copy()
                show["text"] = df["text"].str.slice(0, 120)
                st.dataframe(show, use_container_width=True, hide_index=True)
        except Exception as exc:  # noqa: BLE001
            st.caption(str(exc))
