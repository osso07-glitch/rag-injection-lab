"""Filesystem corpus store: chunks parquet + embeddings npy + meta json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rag_injection_lab.config import CORPORA_DIR
from rag_injection_lab.core.models import Chunk, CorpusInfo, utc_now_iso


def corpus_dir(corpus_id: str) -> Path:
    return CORPORA_DIR / corpus_id


def save_corpus(
    corpus_id: str,
    *,
    name: str,
    chunks: list[Chunk],
    embeddings: np.ndarray,
    embed_model: str,
    provider: str,
    include_poisoned: bool,
    docs: list[dict[str, Any]],
) -> CorpusInfo:
    path = corpus_dir(corpus_id)
    path.mkdir(parents=True, exist_ok=True)

    rows = [c.to_dict() for c in chunks]
    df = pd.DataFrame(rows)
    df.to_parquet(path / "chunks.parquet", index=False)

    emb = np.asarray(embeddings, dtype=np.float32)
    np.save(path / "embeddings.npy", emb)

    info = CorpusInfo(
        corpus_id=corpus_id,
        name=name,
        n_docs=len(docs),
        n_chunks=len(chunks),
        embed_model=embed_model,
        provider=provider,
        created_at=utc_now_iso(),
        path=str(path),
        include_poisoned=include_poisoned,
        doc_names=[d.get("original_name", "") for d in docs],
    )
    meta = info.to_dict()
    meta["docs"] = docs
    (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return info


def load_corpus_meta(corpus_id: str) -> dict[str, Any]:
    path = corpus_dir(corpus_id) / "meta.json"
    if not path.is_file():
        raise FileNotFoundError(f"corpus not found: {corpus_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_chunks(corpus_id: str) -> list[Chunk]:
    path = corpus_dir(corpus_id) / "chunks.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"chunks missing for corpus: {corpus_id}")
    df = pd.read_parquet(path)
    return [Chunk.from_dict(row) for row in df.to_dict(orient="records")]


def load_embeddings(corpus_id: str) -> np.ndarray:
    path = corpus_dir(corpus_id) / "embeddings.npy"
    if not path.is_file():
        raise FileNotFoundError(f"embeddings missing for corpus: {corpus_id}")
    return np.load(path)


def list_corpora() -> list[CorpusInfo]:
    if not CORPORA_DIR.is_dir():
        return []
    out: list[CorpusInfo] = []
    for child in sorted(CORPORA_DIR.iterdir()):
        meta_path = child / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            out.append(CorpusInfo.from_dict(data))
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
    out.sort(key=lambda c: c.created_at, reverse=True)
    return out
