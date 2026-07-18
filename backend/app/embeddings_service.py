"""Local embedding-based semantic search over the book catalogue.

Embeddings are computed with Gemini's embedding model and stored as a JSON list
of floats in ``Book.embedding``. SQLite has no vector type, and for a catalogue
this small (a handful of books, not thousands) we compute cosine similarity in
Python with numpy — no vector DB, no external service beyond the embedding call.

This is deliberately distinct from ``ai_service.semantic_search``, which has
Gemini reason over the whole catalogue in one prompt. Both techniques are kept
on purpose; they showcase different approaches.
"""
import json

import numpy as np

from .ai_service import _client, is_configured  # reuse the cached Gemini client + key check
from .config import settings

# Re-exported so callers can gate on AI availability via this module.
__all__ = [
    "is_configured", "book_embedding_text", "embed_text",
    "encode", "decode", "cosine_similarity", "rank",
]


def book_embedding_text(title: str, author: str, genre=None, summary=None) -> str:
    """Build the text embedded for a book, degrading gracefully if fields are null.

    Books added before the enrich feature won't have genre/summary — that's fine,
    we just embed what's available.
    """
    parts = [f"{title} by {author}."]
    if genre:
        parts.append(f"Genre: {genre}.")
    if summary:
        parts.append(summary)
    return " ".join(parts)


def embed_text(text: str) -> list[float]:
    """Embed a single string, returning its float vector."""
    resp = _client().models.embed_content(model=settings.embedding_model, contents=text)
    return list(resp.embeddings[0].values)


def encode(vec: list[float]) -> str:
    return json.dumps(vec)


def decode(blob) -> list[float] | None:
    if not blob:
        return None
    try:
        return json.loads(blob)
    except (ValueError, TypeError):
        return None


def cosine_similarity(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def rank(query_vec, candidates: list[tuple]) -> list[tuple]:
    """Rank (obj, vec) candidates by cosine similarity to query_vec, best first.

    Returns [(obj, score), ...].
    """
    scored = [(obj, cosine_similarity(query_vec, vec)) for obj, vec in candidates]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored
