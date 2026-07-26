"""Document loading and chunking."""

from rag_injection_lab.ingest.chunking import chunk_text
from rag_injection_lab.ingest.loaders import load_document

__all__ = ["chunk_text", "load_document"]
