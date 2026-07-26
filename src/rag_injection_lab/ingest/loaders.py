"""Load plain-text and PDF documents into strings."""

from __future__ import annotations

from pathlib import Path

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".csv", ".log", ".json", ".yml", ".yaml"}
_PDF_SUFFIXES = {".pdf"}


def load_document(path: Path | str) -> str:
    """Return full text for a supported document path."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"document not found: {p}")

    suffix = p.suffix.lower()
    if suffix in _TEXT_SUFFIXES or suffix == "":
        return p.read_text(encoding="utf-8", errors="replace")
    if suffix in _PDF_SUFFIXES:
        return _load_pdf(p)
    # Best-effort: try utf-8 text
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValueError(f"unsupported document type: {suffix or '(none)'}") from exc


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(f"--- page {i + 1} ---\n{text}")
    return "\n\n".join(parts).strip()


def list_kb_files(directory: Path, patterns: tuple[str, ...] = ("*.txt", "*.md", "*.pdf")) -> list[Path]:
    if not directory.is_dir():
        return []
    found: list[Path] = []
    for pat in patterns:
        found.extend(directory.glob(pat))
    return sorted({p.resolve() for p in found if p.is_file()})
