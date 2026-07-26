"""Chunking unit tests."""

from rag_injection_lab.ingest.chunking import chunk_text


def test_chunk_text_empty():
    assert chunk_text("", doc_id="d1", doc_name="x.txt") == []


def test_chunk_text_overlap_and_ids():
    text = ("Paragraph one. " * 40) + "\n\n" + ("Paragraph two. " * 40)
    chunks = chunk_text(text, doc_id="docA", doc_name="a.txt", chunk_size=200, chunk_overlap=40)
    assert len(chunks) >= 2
    assert chunks[0].chunk_id.startswith("docA:c")
    assert chunks[0].doc_name == "a.txt"
    assert all(c.text for c in chunks)
