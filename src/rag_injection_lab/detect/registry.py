"""Detection rule catalog (Sigma-style metadata; Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass

from rag_injection_lab.core.models import Severity


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    title: str
    severity: str
    description: str
    # compiled check lives in heuristics; this is metadata only for listing


RULES: list[RuleSpec] = [
    RuleSpec(
        rule_id="inj.ignore_previous",
        title="Ignore previous instructions",
        severity=Severity.HIGH.value,
        description="Classic override phrasing inside retrieved content.",
    ),
    RuleSpec(
        rule_id="inj.reveal_system",
        title="Reveal system prompt",
        severity=Severity.HIGH.value,
        description="Attempts to exfiltrate system/developer prompts.",
    ),
    RuleSpec(
        rule_id="inj.roleplay_jailbreak",
        title="Unrestricted / DAN-style role-play",
        severity=Severity.MEDIUM.value,
        description="Role-play jailbreak instructions embedded in documents.",
    ),
    RuleSpec(
        rule_id="inj.system_update",
        title="Fake system / policy update",
        severity=Severity.HIGH.value,
        description="Impersonates a system message or mandatory policy update for the model.",
    ),
    RuleSpec(
        rule_id="inj.exfil_secrets",
        title="Data exfiltration request",
        severity=Severity.CRITICAL.value,
        description="Instructs the model to leak secrets, other users' data, or internal config.",
    ),
    RuleSpec(
        rule_id="inj.developer_mode",
        title="Developer / god mode activation",
        severity=Severity.MEDIUM.value,
        description="Phrases that enable unrestricted 'developer mode'.",
    ),
]


def list_rules() -> list[RuleSpec]:
    return list(RULES)


def rule_by_id(rule_id: str) -> RuleSpec | None:
    for r in RULES:
        if r.rule_id == rule_id:
            return r
    return None
