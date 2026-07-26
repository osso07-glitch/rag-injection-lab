"""SQLite persistence for corpora and query logs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from rag_injection_lab.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS corpora (
    corpus_id     TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    n_docs        INTEGER,
    n_chunks      INTEGER,
    embed_model   TEXT,
    provider      TEXT,
    path          TEXT,
    include_poisoned INTEGER DEFAULT 0,
    meta_json     TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS queries (
    query_id      TEXT PRIMARY KEY,
    corpus_id     TEXT,
    question      TEXT,
    overall_verdict TEXT,
    mitigation_mode TEXT,
    provider      TEXT,
    chat_model    TEXT,
    latency_ms    INTEGER,
    payload_json  TEXT,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_queries_verdict ON queries(overall_verdict);
CREATE INDEX IF NOT EXISTS idx_corpora_created ON corpora(created_at DESC);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dumps(obj: Any) -> str:
    return json.dumps(obj if obj is not None else {}, default=str)


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def record_corpus(meta: dict[str, Any], db_path: Path | None = None) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO corpora
            (corpus_id, name, n_docs, n_chunks, embed_model, provider, path,
             include_poisoned, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meta.get("corpus_id"),
                meta.get("name"),
                meta.get("n_docs"),
                meta.get("n_chunks"),
                meta.get("embed_model"),
                meta.get("provider"),
                meta.get("path"),
                1 if meta.get("include_poisoned") else 0,
                _dumps(meta),
                meta.get("created_at") or _utc_now(),
            ),
        )


def record_query(payload: dict[str, Any], db_path: Path | None = None) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO queries
            (query_id, corpus_id, question, overall_verdict, mitigation_mode,
             provider, chat_model, latency_ms, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("query_id"),
                payload.get("corpus_id"),
                payload.get("question"),
                payload.get("overall_verdict"),
                payload.get("mitigation_mode"),
                payload.get("provider"),
                payload.get("chat_model"),
                payload.get("latency_ms"),
                _dumps(payload),
                payload.get("created_at") or _utc_now(),
            ),
        )


def list_recent_queries(limit: int = 50, db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT query_id, corpus_id, question, overall_verdict, mitigation_mode,
                   provider, chat_model, latency_ms, created_at
            FROM queries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
