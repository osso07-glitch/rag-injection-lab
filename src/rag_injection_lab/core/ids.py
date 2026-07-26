"""ID helpers for corpora, docs, chunks, queries, and findings."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def short_id() -> str:
    return uuid.uuid4().hex[:8]


def slugify_filename(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE).strip("_").lower()
    return slug or "doc"


def make_corpus_id(name: str = "default") -> str:
    return f"{slugify_filename(name)}_{short_id()}"


def make_doc_id(original_name: str) -> str:
    return f"{slugify_filename(original_name)}_{short_id()}"


def make_chunk_id(doc_id: str, index: int) -> str:
    return f"{doc_id}:c{index:04d}"


def make_query_id() -> str:
    return f"query_{utc_stamp()}_{short_id()}"


def make_finding_id() -> str:
    return short_id()
