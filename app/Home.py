"""Home / workspace landing page."""

import streamlit as st

from ui_common import init_app, page_header

init_app()
page_header(
    "RAG Injection Lab",
    "Baseline RAG → indirect prompt injection attacks → detection → mitigation",
)

meta = st.session_state.get("corpus_meta") or {}
last = st.session_state.get("last_query") or {}

col1, col2, col3, col4 = st.columns(4)
col1.metric("Corpus", meta.get("name") or "—")
col2.metric("Docs", meta.get("n_docs") if meta.get("n_docs") is not None else "—")
col3.metric("Chunks", meta.get("n_chunks") if meta.get("n_chunks") is not None else "—")
col4.metric("Last verdict", last.get("overall_verdict") or "—")

st.divider()

if st.session_state.get("corpus_id"):
    st.success(
        f"Active corpus **{meta.get('name') or st.session_state['corpus_id']}** "
        f"(`{st.session_state['corpus_id']}`)."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.page_link("pages/2_Ask.py", label="Ask a question", icon="💬")
    c2.page_link("pages/3_Attack_Lab.py", label="Attack lab", icon="🎯")
    c3.page_link("pages/4_Detections.py", label="Detection log", icon="🛡️")
    c4.page_link("pages/1_Knowledge_Base.py", label="Knowledge base", icon="📚")
else:
    st.info("No corpus loaded yet.")
    st.page_link("pages/1_Knowledge_Base.py", label="Build a knowledge base", icon="📚")

st.divider()
st.subheader("Workflow")
st.markdown(
    """
1. **Knowledge Base** — ingest clean (and optional poisoned) policy docs → chunk → embed  
2. **Ask** — retrieve top-k, answer questions (baseline RAG)  
3. **Attack Lab** — one-click poisoned corpus + suggested questions (Phase 1)  
4. **Detections** — SIEM-style query log: clean vs suspicious (Phase 2+)  
"""
)

st.subheader("Phases")
st.markdown(
    """
| Phase | Scope | Status |
|-------|--------|--------|
| **0** | Baseline RAG (ingest, retrieve, answer) | **In this release** |
| **1** | Attack demos (poisoned docs in retrieval) | Docs + Attack Lab wired |
| **2** | Detection heuristics + query/alert logs | Heuristics + log UI |
| **3** | Mitigation (delimit / sanitize / quarantine) | Modes available on Ask |
"""
)

st.subheader("Why this matters")
st.markdown(
    """
Enterprise RAG systems treat retrieved documents as **trusted context**.  
Attackers who can poison a wiki, ticket, or PDF get **indirect prompt injection**
into the model — without typing anything malicious in the chat box.

This lab maps to **OWASP LLM01 (Prompt Injection)** and related **MITRE ATLAS**
techniques for LLM prompt injection / content injection. It is a **local demo**,
not a production guardrail product.
"""
)

st.caption("Local only · binds **127.0.0.1:8505** · no auth · fictional Acme Corp KB")
