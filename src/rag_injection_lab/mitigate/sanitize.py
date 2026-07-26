"""Sanitize / quarantine suspicious retrieved chunks (Phase 3)."""

from __future__ import annotations

import re

from rag_injection_lab.core.models import MitigationMode, RetrievedChunk, Verdict
from rag_injection_lab.detect.heuristics import scan_text

# Imperative / injection-looking lines to strip when sanitizing
_STRIP_LINE = re.compile(
    r"(?i)^\s*("
    r"ignore\b|disregard\b|forget\b|reveal\b|pretend\b|"
    r"system\s*(update|message|override)|developer\s+message|"
    r"enable\s+developer|jailbreak|you\s+must\s+now|do\s+anything\s+now"
    r").*$",
    re.M,
)


def apply_mitigation(
    retrieved: list[RetrievedChunk],
    mode: MitigationMode | str = MitigationMode.NONE,
) -> list[RetrievedChunk]:
    """Return a (possibly filtered/rewritten) list of chunks for the prompt."""
    m = mode.value if isinstance(mode, MitigationMode) else str(mode)
    if m == MitigationMode.NONE.value or m == MitigationMode.DELIMIT.value:
        # Delimit is handled in prompt.py; content unchanged here
        return list(retrieved)

    out: list[RetrievedChunk] = []
    for r in retrieved:
        hits = scan_text(r.text)
        if m == MitigationMode.QUARANTINE.value:
            if hits:
                # Drop suspicious chunks entirely
                continue
            out.append(r)
            continue
        if m == MitigationMode.SANITIZE.value:
            if hits:
                cleaned = _STRIP_LINE.sub("", r.text)
                cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
                if not cleaned:
                    continue
                out.append(
                    RetrievedChunk(
                        chunk_id=r.chunk_id,
                        doc_id=r.doc_id,
                        doc_name=r.doc_name,
                        text=cleaned,
                        score=r.score,
                        kind=r.kind,
                        index=r.index,
                        verdict=Verdict.SUSPICIOUS.value,
                        matched_rules=[h.rule_id for h in hits],
                    )
                )
            else:
                out.append(r)
            continue
        out.append(r)
    return out
