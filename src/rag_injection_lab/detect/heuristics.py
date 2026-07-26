"""Regex/keyword heuristics for indirect prompt-injection payloads.

Phase 2 core. Designed like lightweight Sigma rules: high-signal phrases
with explainable evidence snippets. Not a complete defense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_injection_lab.core.models import DetectionHit, Severity, Verdict
from rag_injection_lab.detect.registry import RULES, rule_by_id


@dataclass(frozen=True)
class _PatternRule:
    rule_id: str
    patterns: tuple[re.Pattern[str], ...]


_RULE_PATTERNS: list[_PatternRule] = [
    _PatternRule(
        "inj.ignore_previous",
        (
            re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
            re.compile(r"disregard\s+(your\s+)?(previous|prior|system)\s+(instructions?|prompt)", re.I),
            re.compile(r"forget\s+(everything|all)\s+(you|your)\s+(know|instructions?)", re.I),
        ),
    ),
    _PatternRule(
        "inj.reveal_system",
        (
            re.compile(r"reveal\s+(the\s+)?(system|developer)\s+prompt", re.I),
            re.compile(r"print\s+(your\s+)?(system|hidden)\s+(prompt|instructions?)", re.I),
            re.compile(r"show\s+(me\s+)?(your\s+)?(system\s+prompt|initial\s+instructions?)", re.I),
        ),
    ),
    _PatternRule(
        "inj.roleplay_jailbreak",
        (
            re.compile(r"pretend\s+you\s+are\s+(an?\s+)?unrestricted", re.I),
            re.compile(r"\bDAN\b.*\b(do\s+anything\s+now)?", re.I),
            re.compile(r"jailbreak\s+mode", re.I),
            re.compile(r"no\s+ethical\s+(guidelines|constraints|limits)", re.I),
        ),
    ),
    _PatternRule(
        "inj.system_update",
        (
            re.compile(r"\[?\s*system\s*(update|message|override)\s*\]?", re.I),
            re.compile(r"important\s+system\s+update", re.I),
            re.compile(r"as\s+of\s+this\s+update,?\s+you\s+must", re.I),
            re.compile(r"developer\s+message\s*:", re.I),
        ),
    ),
    _PatternRule(
        "inj.exfil_secrets",
        (
            re.compile(r"(leak|exfiltrate|dump)\s+(all\s+)?(secrets?|api\s*keys?|credentials?)", re.I),
            re.compile(r"reveal\s+(other\s+users?|internal)\s+(data|info|information|config)", re.I),
            re.compile(r"include\s+(the\s+)?(api\s*key|password|secret)\s+in\s+your\s+(answer|response)", re.I),
            re.compile(r"send\s+.*\s+to\s+https?://", re.I),
        ),
    ),
    _PatternRule(
        "inj.developer_mode",
        (
            re.compile(r"enable\s+developer\s+mode", re.I),
            re.compile(r"god\s+mode\s+(enabled|activated|on)", re.I),
            re.compile(r"you\s+are\s+now\s+in\s+(admin|developer|unrestricted)\s+mode", re.I),
        ),
    ),
]


def scan_text(text: str) -> list[DetectionHit]:
    """Return all heuristic hits for a single chunk or document string."""
    if not text or not text.strip():
        return []
    hits: list[DetectionHit] = []
    seen: set[str] = set()
    for rule in _RULE_PATTERNS:
        for pat in rule.patterns:
            m = pat.search(text)
            if not m:
                continue
            if rule.rule_id in seen:
                break
            seen.add(rule.rule_id)
            meta = rule_by_id(rule.rule_id)
            severity = meta.severity if meta else Severity.MEDIUM.value
            title = meta.title if meta else rule.rule_id
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            evidence = text[start:end].replace("\n", " ").strip()
            hits.append(
                DetectionHit(
                    rule_id=rule.rule_id,
                    severity=severity,
                    message=title,
                    evidence=evidence,
                )
            )
            break
    return hits


def verdict_from_hits(hits: list[DetectionHit]) -> str:
    if not hits:
        return Verdict.CLEAN.value
    return Verdict.SUSPICIOUS.value


def list_rule_ids() -> list[str]:
    return [r.rule_id for r in RULES]
