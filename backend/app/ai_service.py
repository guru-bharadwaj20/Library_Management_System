"""LLM-backed features (natural-language search, recommendations) via Claude.

Kept deliberately decoupled from the ORM — callers pass plain dicts/lists, so
this module is easy to unit-test without a database. The model is asked to
return JSON; we parse defensively and the router validates every returned
book_id against the real catalogue, so a hallucinated id is simply dropped.
"""
import json

import anthropic

from .config import settings

# Small catalogue → passing it inline is fine. For a large library this would
# move to embeddings + a vector store (pgvector) so we only send top-K matches.
_MAX_TOKENS = 1024


def is_configured() -> bool:
    return bool(settings.anthropic_api_key)


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _catalogue_lines(books: list[dict]) -> str:
    return "\n".join(
        f"- {b['book_id']} | {b['title']} | {b['author']} | available: {b['available_copies']}"
        for b in books
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence if the model added one.
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    return json.loads(text)  # JSONDecodeError is a ValueError — caught upstream


def _ask_json(system: str, user: str) -> dict:
    resp = _client().messages.create(
        model=settings.ai_model,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return _extract_json(text)


def semantic_search(query: str, books: list[dict]) -> list[dict]:
    """Return [{book_id, reason}, ...] best-first for a natural-language query."""
    system = (
        "You are a library search assistant. You are given a catalogue of books "
        "and a patron's natural-language request. Choose the books that best match "
        "the request. Only use book_id values that appear in the catalogue — never "
        "invent one. Return at most 5, most relevant first. Respond with ONLY a JSON "
        'object of the form {"results": [{"book_id": "B001", "reason": "one short sentence"}]}. '
        "If nothing matches, return an empty results list."
    )
    user = f"Catalogue:\n{_catalogue_lines(books)}\n\nPatron request: {query!r}"
    return _ask_json(system, user).get("results", [])


def recommend(borrowed: list[tuple[str, str]], books: list[dict]) -> list[dict]:
    """Return [{book_id, reason}, ...] recommendations from borrow history.

    ``borrowed`` is a list of (book_id, title) the reader has already had.
    """
    system = (
        "You are a librarian giving personalized reading recommendations. Given the "
        "books a reader has already borrowed and the current catalogue, recommend up "
        "to 3 books they have NOT already borrowed. Only use book_id values from the "
        "catalogue, and never recommend a book already in their history. Respond with "
        'ONLY a JSON object of the form {"recommendations": [{"book_id": "B001", '
        '"reason": "one short sentence"}]}.'
    )
    history = ", ".join(f"{title} ({bid})" for bid, title in borrowed) or "nothing yet"
    user = f"Catalogue:\n{_catalogue_lines(books)}\n\nAlready borrowed: {history}"
    return _ask_json(system, user).get("recommendations", [])
