"""Build a corpus: load docs → chunk → embed → persist."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from rag_injection_lab.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    KB_CLEAN_DIR,
    KB_POISONED_DIR,
    PROVIDER,
    UPLOADS_DIR,
    ensure_runtime_dirs,
)
from rag_injection_lab.core.ids import make_corpus_id, make_doc_id
from rag_injection_lab.core.models import DocKind, DocumentMeta, IngestReport, utc_now_iso
from rag_injection_lab.ingest.chunking import chunk_text
from rag_injection_lab.ingest.loaders import list_kb_files, load_document
from rag_injection_lab.meta import db as meta_db
from rag_injection_lab.rag.embeddings import get_embedder
from rag_injection_lab.rag.store import save_corpus


def list_clean_kb() -> list[Path]:
    ensure_runtime_dirs()
    return list_kb_files(KB_CLEAN_DIR)


def list_poisoned_kb() -> list[Path]:
    ensure_runtime_dirs()
    return list_kb_files(KB_POISONED_DIR)


def store_upload(path: Path, original_name: str | None = None) -> Path:
    """Copy a user file into data/_uploads/ and return destination path."""
    ensure_runtime_dirs()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    name = original_name or path.name
    dest = UPLOADS_DIR / name
    if path.resolve() != dest.resolve():
        shutil.copy2(path, dest)
    return dest


def build_corpus(
    *,
    name: str = "default",
    include_clean: bool = True,
    include_poisoned: bool = False,
    extra_paths: list[Path] | None = None,
    provider: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    corpus_id: str | None = None,
) -> IngestReport:
    """Ingest selected knowledge-base files into a new corpus."""
    ensure_runtime_dirs()
    paths: list[tuple[Path, str]] = []  # path, kind

    if include_clean:
        for p in list_clean_kb():
            paths.append((p, DocKind.CLEAN.value))
    if include_poisoned:
        for p in list_poisoned_kb():
            paths.append((p, DocKind.POISONED.value))
    for p in extra_paths or []:
        paths.append((Path(p), DocKind.UPLOAD.value))

    if not paths:
        raise ValueError("no documents selected for ingest")

    prov = (provider or PROVIDER).lower()
    embedder = get_embedder(prov)
    cid = corpus_id or make_corpus_id(name)

    all_chunks = []
    docs_meta: list[dict[str, Any]] = []
    total_chars = 0
    warnings: list[str] = []

    for path, kind in paths:
        try:
            text = load_document(path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"skip {path.name}: {exc}")
            continue
        doc_id = make_doc_id(path.name)
        raw = path.read_bytes()
        meta = DocumentMeta(
            doc_id=doc_id,
            original_name=path.name,
            source_path=str(path.resolve()),
            kind=kind,
            n_bytes=len(raw),
            n_chars=len(text),
            created_at=utc_now_iso(),
            sha256=hashlib.sha256(raw).hexdigest(),
        )
        docs_meta.append(meta.to_dict())
        total_chars += len(text)
        chunks = chunk_text(
            text,
            doc_id=doc_id,
            doc_name=path.name,
            kind=kind,
            chunk_size=chunk_size or CHUNK_SIZE,
            chunk_overlap=chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP,
        )
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError("no chunks produced from selected documents")

    texts = [c.text for c in all_chunks]
    embeddings = embedder.embed(texts)

    info = save_corpus(
        cid,
        name=name,
        chunks=all_chunks,
        embeddings=embeddings,
        embed_model=embedder.model_name,
        provider=prov,
        include_poisoned=include_poisoned,
        docs=docs_meta,
    )
    meta_db.record_corpus(info.to_dict())

    return IngestReport(
        corpus_id=cid,
        n_docs=len(docs_meta),
        n_chunks=len(all_chunks),
        n_chars=total_chars,
        embed_model=embedder.model_name,
        provider=prov,
        docs=docs_meta,
        created_at=info.created_at,
        warnings=warnings,
    )
