"""Domain models and service DTOs for v0.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DocKind(str, Enum):
    CLEAN = "clean"
    POISONED = "poisoned"
    UPLOAD = "upload"


class Verdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MitigationMode(str, Enum):
    NONE = "none"
    DELIMIT = "delimit"
    SANITIZE = "sanitize"
    QUARANTINE = "quarantine"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(v: Any) -> Any:
    return v.value if isinstance(v, Enum) else v


def _filter_fields(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    allowed = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in allowed}


@dataclass
class DocumentMeta:
    doc_id: str
    original_name: str
    source_path: str
    kind: str  # DocKind value
    n_bytes: int
    n_chars: int
    created_at: str
    sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentMeta:
        return cls(**_filter_fields(cls, data))


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_name: str
    index: int
    text: str
    kind: str = DocKind.CLEAN.value
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        return cls(**_filter_fields(cls, data))


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    doc_name: str
    text: str
    score: float
    kind: str = DocKind.CLEAN.value
    index: int = 0
    verdict: str = Verdict.UNKNOWN.value
    matched_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetrievedChunk:
        return cls(**_filter_fields(cls, data))


@dataclass
class DetectionHit:
    rule_id: str
    severity: str
    message: str
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryLog:
    """SIEM-style retrieval/generation log row (Phase 0+)."""

    query_id: str
    corpus_id: str
    question: str
    answer: str
    top_k: int
    provider: str
    chat_model: str
    embed_model: str
    created_at: str
    retrieved: list[dict[str, Any]] = field(default_factory=list)
    overall_verdict: str = Verdict.UNKNOWN.value
    mitigation_mode: str = MitigationMode.NONE.value
    detection_hits: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueryLog:
        return cls(**_filter_fields(cls, data))


@dataclass
class CorpusInfo:
    corpus_id: str
    name: str
    n_docs: int
    n_chunks: int
    embed_model: str
    provider: str
    created_at: str
    path: str
    include_poisoned: bool = False
    doc_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorpusInfo:
        return cls(**_filter_fields(cls, data))


@dataclass
class IngestReport:
    corpus_id: str
    n_docs: int
    n_chunks: int
    n_chars: int
    embed_model: str
    provider: str
    docs: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
