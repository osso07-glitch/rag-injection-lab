"""Simple character-window chunking with overlap."""

from __future__ import annotations

from rag_injection_lab.config import CHUNK_OVERLAP, CHUNK_SIZE
from rag_injection_lab.core.ids import make_chunk_id
from rag_injection_lab.core.models import Chunk, DocKind


def chunk_text(
    text: str,
    *,
    doc_id: str,
    doc_name: str,
    kind: str = DocKind.CLEAN.value,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split text into overlapping character windows.

    Prefers breaking near paragraph or sentence boundaries when the window
    lands mid-block; falls back to hard cuts for long runs without whitespace.
    """
    size = chunk_size if chunk_size is not None else CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP
    if size < 50:
        raise ValueError("chunk_size must be >= 50")
    if overlap < 0 or overlap >= size:
        raise ValueError("chunk_overlap must be in [0, chunk_size)")

    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []

    chunks: list[Chunk] = []
    start = 0
    n = len(cleaned)
    index = 0

    while start < n:
        end = min(start + size, n)
        if end < n:
            window = cleaned[start:end]
            # Prefer paragraph break, then sentence, then whitespace
            break_at = _best_break(window)
            if break_at is not None and break_at > size // 4:
                end = start + break_at

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(doc_id, index),
                    doc_id=doc_id,
                    doc_name=doc_name,
                    index=index,
                    text=piece,
                    kind=kind,
                    start_char=start,
                    end_char=end,
                )
            )
            index += 1

        if end >= n:
            break
        start = max(end - overlap, start + 1)

    return chunks


def _best_break(window: str) -> int | None:
    for sep in ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "):
        pos = window.rfind(sep)
        if pos != -1:
            return pos + len(sep)
    return None
