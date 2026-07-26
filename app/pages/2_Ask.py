"""Ask — baseline RAG chat against the active corpus."""

from __future__ import annotations

import importlib

import streamlit as st

import ui_common as _ui_common

importlib.reload(_ui_common)
from ui_common import init_app, page_header, require_corpus  # noqa: E402

from rag_injection_lab.core.models import MitigationMode
from rag_injection_lab.services.query_service import ask

init_app()
page_header("Ask", "Retrieve top-k chunks and generate an answer")

corpus_id = require_corpus()

with st.sidebar:
    st.subheader("Query options")
    top_k = st.slider("top_k", min_value=1, max_value=10, value=4)
    provider = st.selectbox(
        "Provider",
        options=["mock", "openai", "anthropic"],
        index=["mock", "openai", "anthropic"].index(st.session_state.get("provider", "mock"))
        if st.session_state.get("provider", "mock") in ("mock", "openai", "anthropic")
        else 0,
    )
    st.session_state.provider = provider
    run_detection = st.checkbox("Run detection heuristics", value=st.session_state.get("run_detection", True))
    st.session_state.run_detection = run_detection
    mitigation = st.selectbox(
        "Mitigation (Phase 3)",
        options=["none", "delimit", "sanitize", "quarantine"],
        index=["none", "delimit", "sanitize", "quarantine"].index(
            st.session_state.get("mitigation", "none")
        )
        if st.session_state.get("mitigation", "none")
        in ("none", "delimit", "sanitize", "quarantine")
        else 0,
        help="none = baseline. delimit wraps context as data. sanitize/quarantine strip or drop hits.",
    )
    st.session_state.mitigation = mitigation

suggested = [
    "How many vacation days do full-time employees get?",
    "How do I reset my corporate password?",
    "What is the hybrid work policy?",
    "What is the annual learning stipend?",
    "Who do I contact about phishing?",
]
pick = st.selectbox("Suggested questions", ["(type your own)"] + suggested)
question = st.text_area(
    "Question",
    value="" if pick == "(type your own)" else pick,
    height=100,
)

if st.button("Ask", type="primary", disabled=not question.strip()):
    try:
        with st.spinner("Retrieving and generating…"):
            log = ask(
                corpus_id,
                question.strip(),
                top_k=top_k,
                provider=provider,
                run_detection=run_detection,
                mitigation=MitigationMode(mitigation),
            )
        st.session_state.last_query = log.to_dict()
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        st.stop()

last = st.session_state.get("last_query")
if last:
    st.divider()
    v = last.get("overall_verdict", "unknown")
    if v == "suspicious":
        st.error(f"Verdict: **{v}** · mitigation=`{last.get('mitigation_mode')}` · {last.get('latency_ms')} ms")
    elif v == "clean":
        st.success(f"Verdict: **{v}** · mitigation=`{last.get('mitigation_mode')}` · {last.get('latency_ms')} ms")
    else:
        st.info(f"Verdict: **{v}** · {last.get('latency_ms')} ms")

    st.subheader("Answer")
    if last.get("error"):
        st.error(last["error"])
    st.markdown(last.get("answer") or "_(empty)_")

    st.subheader("Retrieved chunks")
    for i, r in enumerate(last.get("retrieved") or [], 1):
        flag = "🚨" if r.get("verdict") == "suspicious" else "✅"
        with st.expander(
            f"{flag} [{i}] {r.get('doc_name')} · score={r.get('score', 0):.3f} · {r.get('verdict')}"
        ):
            if r.get("matched_rules"):
                st.warning("Rules: " + ", ".join(r["matched_rules"]))
            st.code(r.get("text") or "", language="text")

    if last.get("detection_hits"):
        st.subheader("Detection hits")
        for h in last["detection_hits"]:
            st.markdown(
                f"- **{h.get('rule_id')}** ({h.get('severity')}): {h.get('message')}  \n"
                f"  `{h.get('evidence', '')[:160]}`"
            )
