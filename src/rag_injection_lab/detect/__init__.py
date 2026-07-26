"""Detection rules for indirect prompt injection (Phase 2)."""

from rag_injection_lab.detect.heuristics import scan_text
from rag_injection_lab.detect.registry import list_rules

__all__ = ["scan_text", "list_rules"]
