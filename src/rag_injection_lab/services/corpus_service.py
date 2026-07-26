"""Corpus inventory helpers."""

from __future__ import annotations

from rag_injection_lab.config import ensure_runtime_dirs
from rag_injection_lab.core.models import CorpusInfo
from rag_injection_lab.rag.store import list_corpora, load_chunks, load_corpus_meta


def get_corpora() -> list[CorpusInfo]:
    ensure_runtime_dirs()
    return list_corpora()


def get_corpus(corpus_id: str) -> dict:
    ensure_runtime_dirs()
    return load_corpus_meta(corpus_id)


def get_chunk_preview(corpus_id: str, limit: int = 20) -> list[dict]:
    ensure_runtime_dirs()
    chunks = load_chunks(corpus_id)
    return [c.to_dict() for c in chunks[:limit]]
