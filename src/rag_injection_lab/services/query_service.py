"""Retrieve + (optional) detect/mitigate + generate answer."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rag_injection_lab.config import (
    CHAT_MODEL,
    DEFAULT_MITIGATION,
    ENABLE_DETECTION,
    ENABLE_MITIGATION,
    FINDINGS_DIR,
    PROVIDER,
    TOP_K,
    ensure_runtime_dirs,
)
from rag_injection_lab.core.ids import make_query_id
from rag_injection_lab.core.models import (
    MitigationMode,
    QueryLog,
    RetrievedChunk,
    Verdict,
    utc_now_iso,
)
from rag_injection_lab.detect.heuristics import scan_text, verdict_from_hits
from rag_injection_lab.meta import db as meta_db
from rag_injection_lab.mitigate.sanitize import apply_mitigation
from rag_injection_lab.rag.embeddings import cosine_topk, get_embedder
from rag_injection_lab.rag.generate import get_generator
from rag_injection_lab.rag.prompt import build_messages
from rag_injection_lab.rag.store import load_chunks, load_corpus_meta, load_embeddings


def ask(
    corpus_id: str,
    question: str,
    *,
    top_k: int | None = None,
    provider: str | None = None,
    chat_model: str | None = None,
    run_detection: bool | None = None,
    mitigation: MitigationMode | str | None = None,
    persist: bool = True,
) -> QueryLog:
    """End-to-end RAG query against an existing corpus.

    Defaults for detection/mitigation come from env flags when arguments are
    omitted (``None``):

    - ``RAG_LAB_ENABLE_DETECTION`` (default true)
    - ``RAG_LAB_ENABLE_MITIGATION`` + ``RAG_LAB_DEFAULT_MITIGATION`` (default off)
    """
    ensure_runtime_dirs()
    t0 = time.perf_counter()
    qid = make_query_id()
    prov = (provider or PROVIDER).lower()
    k = top_k if top_k is not None else TOP_K
    do_detect = ENABLE_DETECTION if run_detection is None else bool(run_detection)

    if mitigation is None:
        if ENABLE_MITIGATION:
            try:
                mit_mode = MitigationMode(DEFAULT_MITIGATION)
            except ValueError:
                mit_mode = MitigationMode.SANITIZE
        else:
            mit_mode = MitigationMode.NONE
    else:
        mit_mode = (
            mitigation
            if isinstance(mitigation, MitigationMode)
            else MitigationMode(str(mitigation))
        )

    meta = load_corpus_meta(corpus_id)
    chunks = load_chunks(corpus_id)
    matrix = load_embeddings(corpus_id)

    # Use same provider family for query embedding; prefer corpus embed model label
    embedder = get_embedder(meta.get("provider") or prov, model=meta.get("embed_model"))
    # If corpus was built with local-hash but we request openai, dims may mismatch —
    # always re-embed query with a backend that matches matrix dim when possible.
    q_vec = embedder.embed([question])[0]
    if q_vec.shape[0] != matrix.shape[1]:
        # Fall back to local hash if dims differ (common when corpus is offline-built)
        from rag_injection_lab.rag.embeddings import LocalHashEmbedder

        embedder = LocalHashEmbedder()
        q_vec = embedder.embed([question])[0]
        if q_vec.shape[0] != matrix.shape[1]:
            raise ValueError(
                f"embedding dim mismatch: query={q_vec.shape[0]} corpus={matrix.shape[1]}. "
                "Rebuild the corpus with the same provider."
            )

    idx, scores = cosine_topk(q_vec, matrix, k)
    retrieved: list[RetrievedChunk] = []
    all_hits: list[dict[str, Any]] = []

    for i, score in zip(idx.tolist(), scores.tolist(), strict=True):
        c = chunks[i]
        hits = scan_text(c.text) if do_detect else []
        verdict = verdict_from_hits(hits) if do_detect else Verdict.UNKNOWN.value
        rc = RetrievedChunk(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            doc_name=c.doc_name,
            text=c.text,
            score=float(score),
            kind=c.kind,
            index=c.index,
            verdict=verdict,
            matched_rules=[h.rule_id for h in hits],
        )
        retrieved.append(rc)
        for h in hits:
            all_hits.append({**h.to_dict(), "chunk_id": c.chunk_id, "doc_name": c.doc_name})

    overall = (
        Verdict.SUSPICIOUS.value
        if any(r.verdict == Verdict.SUSPICIOUS.value for r in retrieved)
        else (Verdict.CLEAN.value if do_detect else Verdict.UNKNOWN.value)
    )
    prompt_chunks = apply_mitigation(retrieved, mit_mode)
    messages = build_messages(question, prompt_chunks, mitigation=mit_mode)

    generator = get_generator(prov, model=chat_model or CHAT_MODEL)
    error: str | None = None
    try:
        answer = generator.complete(messages)
    except Exception as exc:  # noqa: BLE001
        answer = ""
        error = str(exc)

    latency_ms = int((time.perf_counter() - t0) * 1000)
    log = QueryLog(
        query_id=qid,
        corpus_id=corpus_id,
        question=question,
        answer=answer,
        top_k=k,
        provider=generator.provider,
        chat_model=generator.model_name,
        embed_model=embedder.model_name,
        created_at=utc_now_iso(),
        retrieved=[r.to_dict() for r in retrieved],
        overall_verdict=overall,
        mitigation_mode=mit_mode.value,
        detection_hits=all_hits,
        latency_ms=latency_ms,
        error=error,
    )

    if persist:
        _persist_query(log)

    return log


def _persist_query(log: QueryLog) -> Path:
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    dest = FINDINGS_DIR / log.query_id
    dest.mkdir(parents=True, exist_ok=True)
    payload = log.to_dict()
    (dest / "query.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # SIEM-ish one-line alert when suspicious
    alert = {
        "timestamp": log.created_at,
        "query_id": log.query_id,
        "corpus_id": log.corpus_id,
        "verdict": log.overall_verdict,
        "severity": _max_severity(log.detection_hits),
        "rule_ids": sorted({h.get("rule_id", "") for h in log.detection_hits}),
        "question": log.question[:200],
        "n_retrieved": len(log.retrieved),
        "mitigation": log.mitigation_mode,
    }
    (dest / "alert.json").write_text(json.dumps(alert, indent=2), encoding="utf-8")
    meta_db.record_query(payload)
    return dest


def _max_severity(hits: list[dict[str, Any]]) -> str:
    order = ["info", "low", "medium", "high", "critical"]
    best = "info"
    for h in hits:
        s = str(h.get("severity", "info")).lower()
        if s in order and order.index(s) > order.index(best):
            best = s
    return best if hits else "info"


def list_query_logs(limit: int = 50) -> list[dict[str, Any]]:
    ensure_runtime_dirs()
    if not FINDINGS_DIR.is_dir():
        return []
    logs: list[dict[str, Any]] = []
    for child in sorted(FINDINGS_DIR.iterdir(), reverse=True):
        qpath = child / "query.json"
        if not qpath.is_file():
            continue
        try:
            logs.append(json.loads(qpath.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
        if len(logs) >= limit:
            break
    return logs
