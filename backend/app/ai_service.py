"""LLM-backed features (natural-language search, recommendations, metadata
enrichment) via Google Gemini.

Kept deliberately decoupled from the ORM — callers pass plain dicts/lists, so
this module is easy to unit-test without a database. We ask Gemini for JSON
(`response_mime_type="application/json"`) and parse defensively; the router
validates every returned book_id against the real catalogue, so a hallucinated
id is simply dropped.
"""
import json
from functools import lru_cache

from google import genai
from google.genai import types

from .config import settings

_MAX_TOKENS = 1024


def is_configured() -> bool:
    return bool(settings.gemini_api_key)


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    # Cache the client for the process lifetime. A fresh Client per call gets
    # garbage-collected mid-request, and its finalizer closes the shared httpx
    # client out from under the in-flight request ("client has been closed").
    return genai.Client(api_key=settings.gemini_api_key)


def _catalogue_lines(books: list[dict]) -> str:
    return "\n".join(
        f"- {b['book_id']} | {b['title']} | {b['author']} | available: {b['available_copies']}"
        for b in books
    )


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence if the model added one.
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    return json.loads(text)  # JSONDecodeError is a ValueError — caught upstream


def _ask_json(system: str, user: str) -> dict:
    resp = _client().models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            max_output_tokens=_MAX_TOKENS,
            temperature=0.2,
        ),
    )
    return _extract_json(resp.text)


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


def enrich_book(title: str, author: str) -> dict:
    """Suggest catalogue metadata for a book from its title/author.

    Returns {"genre": str, "reading_level": str, "summary": str}. Values may be
    empty strings if the model is unsure — the caller decides what to keep.
    """
    system = (
        "You are a library cataloguing assistant. Given a book's title and author, "
        "provide concise catalogue metadata. Respond with ONLY a JSON object of the "
        'form {"genre": "...", "reading_level": "...", "summary": "..."}. '
        "genre: one or two words (e.g. 'Dystopian fiction'). "
        "reading_level: one of 'Children', 'Young Adult', 'Adult', or 'Academic'. "
        "summary: one or two sentences, spoiler-free. "
        "If you are not confident the book exists, use empty strings rather than guessing."
    )
    user = f"Title: {title!r}\nAuthor: {author!r}"
    data = _ask_json(system, user)
    return {
        "genre": (data.get("genre") or "").strip(),
        "reading_level": (data.get("reading_level") or "").strip(),
        "summary": (data.get("summary") or "").strip(),
    }
