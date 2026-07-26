"""Detections — SIEM-style log of retrieval verdicts."""

from __future__ import annotations

import importlib

import pandas as pd
import streamlit as st

import ui_common as _ui_common

importlib.reload(_ui_common)
from ui_common import init_app, page_header  # noqa: E402

from rag_injection_lab.detect.registry import list_rules
from rag_injection_lab.meta.db import list_recent_queries
from rag_injection_lab.services.query_service import list_query_logs


def _max_sev(hits: list) -> str:
    order = ["info", "low", "medium", "high", "critical"]
    best = "info"
    for h in hits:
        s = str(h.get("severity", "info")).lower()
        if s in order and order.index(s) > order.index(best):
            best = s
    return best if hits else "info"


init_app()
page_header("Detections", "Query log framed like SIEM alerts (Phase 2)")

st.markdown(
    """
Each `ask` writes `data/findings/{query_id}/query.json` and `alert.json`.  
Suspicious rows mean **retrieved context** matched injection heuristics — not that the
user typed a jailbreak.
"""
)

tab_log, tab_rules = st.tabs(["Alert log", "Rule catalog"])

with tab_log:
    logs = list_query_logs(limit=100)
    if not logs:
        # fall back to sqlite summary
        rows = list_recent_queries(limit=100)
        if not rows:
            st.info("No queries yet. Run **Ask** or **Attack Lab** first.")
        else:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        flat = []
        for r in logs:
            hits = r.get("detection_hits") or []
            flat.append(
                {
                    "timestamp": r.get("created_at"),
                    "query_id": r.get("query_id"),
                    "verdict": r.get("overall_verdict"),
                    "severity": _max_sev(hits),
                    "rules": ", ".join(sorted({h.get("rule_id", "") for h in hits})) or "—",
                    "mitigation": r.get("mitigation_mode"),
                    "provider": r.get("provider"),
                    "latency_ms": r.get("latency_ms"),
                    "question": (r.get("question") or "")[:80],
                    "n_retrieved": len(r.get("retrieved") or []),
                }
            )
        df = pd.DataFrame(flat)

        filter_v = st.multiselect(
            "Verdict filter",
            options=sorted(df["verdict"].dropna().unique().tolist()) if not df.empty else [],
            default=["suspicious"]
            if not df.empty and "suspicious" in set(df["verdict"])
            else (df["verdict"].unique().tolist() if not df.empty else []),
        )
        view = df[df["verdict"].isin(filter_v)] if filter_v else df

        st.dataframe(view, use_container_width=True, hide_index=True)
        n_sus = int((view["verdict"] == "suspicious").sum()) if not view.empty else 0
        if n_sus:
            st.error(f"{n_sus} suspicious alert(s) in current filter")

        st.subheader("Inspect query")
        ids = [r.get("query_id") for r in logs if r.get("query_id")]
        if ids:
            qid = st.selectbox("query_id", ids)
            detail = next(r for r in logs if r.get("query_id") == qid)
            st.json(
                {
                    "query_id": detail.get("query_id"),
                    "verdict": detail.get("overall_verdict"),
                    "mitigation": detail.get("mitigation_mode"),
                    "question": detail.get("question"),
                    "answer": (detail.get("answer") or "")[:800],
                    "detection_hits": detail.get("detection_hits"),
                    "retrieved": [
                        {
                            "doc_name": x.get("doc_name"),
                            "score": x.get("score"),
                            "verdict": x.get("verdict"),
                            "rules": x.get("matched_rules"),
                        }
                        for x in (detail.get("retrieved") or [])
                    ],
                }
            )

with tab_rules:
    rules = list_rules()
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "rule_id": r.rule_id,
                    "severity": r.severity,
                    "title": r.title,
                    "description": r.description,
                }
                for r in rules
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Heuristics are high-signal demos — expect evasion and some false positives on "
        "legitimate security-policy language. Frame as first-line detection engineering, "
        "not a complete control."
    )
