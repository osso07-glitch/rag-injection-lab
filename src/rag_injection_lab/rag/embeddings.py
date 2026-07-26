"""Embedding backends: OpenAI or local hash (offline / tests)."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import numpy as np

from rag_injection_lab.config import EMBED_MODEL, PROVIDER

_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.I)


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return shape (n, d) float32 L2-normalized vectors."""
        ...


class LocalHashEmbedder:
    """Deterministic bag-of-hash embedding — no API, good enough for demos/tests."""

    def __init__(self, dim: int = 256, model_name: str = "local-hash-v1") -> None:
        self.dim = dim
        self.model_name = model_name

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        rows = [self._one(t) for t in texts]
        return np.vstack(rows)

    def _one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            tokens = ["empty"]
        for tok in tokens:
            h = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec


class OpenAIEmbedder:
    def __init__(self, model: str | None = None) -> None:
        self.model_name = model or EMBED_MODEL

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 1), dtype=np.float32)
        from openai import OpenAI

        client = OpenAI()
        # API limit: batch reasonably
        out: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = client.embeddings.create(model=self.model_name, input=batch)
            # Ensure order by index
            ordered = sorted(resp.data, key=lambda d: d.index)
            out.extend([d.embedding for d in ordered])
        arr = np.asarray(out, dtype=np.float32)
        # L2 normalize for cosine via dot product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return arr / norms


def get_embedder(provider: str | None = None, model: str | None = None) -> Embedder:
    prov = (provider or PROVIDER).lower()
    if prov in ("mock", "local", "hash"):
        return LocalHashEmbedder()
    if prov == "openai":
        import os

        if not os.environ.get("OPENAI_API_KEY"):
            # Graceful offline fallback
            return LocalHashEmbedder(model_name="local-hash-fallback")
        return OpenAIEmbedder(model=model)
    if prov == "anthropic":
        # Anthropic has no first-class embed API in this lab — use local hash
        # or OpenAI embeddings if key present.
        import os

        if os.environ.get("OPENAI_API_KEY"):
            return OpenAIEmbedder(model=model)
        return LocalHashEmbedder(model_name="local-hash-anthropic-fallback")
    return LocalHashEmbedder()


def cosine_topk(
    query_vec: np.ndarray,
    matrix: np.ndarray,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (indices, scores) for top-k cosine similarity (vectors assumed L2-normed)."""
    if matrix.size == 0 or query_vec.size == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
    q = query_vec.reshape(-1)
    if q.shape[0] != matrix.shape[1]:
        raise ValueError(f"dim mismatch: query {q.shape[0]} vs store {matrix.shape[1]}")
    scores = matrix @ q
    k = min(k, len(scores))
    if k <= 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
    # argpartition then sort the top-k
    idx = np.argpartition(-scores, kth=k - 1)[:k]
    idx = idx[np.argsort(-scores[idx])]
    return idx.astype(np.int64), scores[idx].astype(np.float32)


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(vec))
    if n == 0 or math.isclose(n, 0.0):
        return vec.astype(np.float32)
    return (vec / n).astype(np.float32)
