"""AI-powered endpoints (Google Gemini): natural-language search, personalized
recommendations, and catalogue metadata enrichment.

All degrade gracefully: if no GEMINI_API_KEY is configured they return 503, so
the rest of the system works without AI. Every book_id the model returns for
search/recommend is validated against the live catalogue before being sent back.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from google.genai import errors as genai_errors
from sqlalchemy.orm import Session

from .. import ai_service, embeddings_service
from ..database import get_db
from ..deps import get_current_user, require_librarian
from ..models import Book, BorrowRecord, Student
from ..schemas import (
    AIEnrichRequest,
    AIEnrichResponse,
    AIHit,
    AIRecommendResponse,
    AISearchRequest,
    AISearchResponse,
    SemanticHit,
    SemanticSearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

_UPSTREAM = status.HTTP_502_BAD_GATEWAY


def _require_ai():
    if not ai_service.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI features are not configured. Set GEMINI_API_KEY in the backend .env.",
        )


def _run_ai(fn, *args, **kwargs):
    """Call an ai_service function, turning any failure into a clean 502.

    The AI provider is an external dependency — a bad key, a timeout, a garbled
    response, or an SDK quirk must never surface as a 500.
    """
    try:
        return fn(*args, **kwargs)
    except genai_errors.APIError as exc:
        raise HTTPException(_UPSTREAM, f"AI request failed: {exc}")
    except (ValueError, KeyError):
        raise HTTPException(_UPSTREAM, "AI returned an unparseable response; try again.")
    except Exception as exc:  # noqa: BLE001 — external call: fail soft, never 500
        raise HTTPException(_UPSTREAM, f"AI request failed: {exc}")


def _books_payload(db: Session) -> list[dict]:
    return [
        {
            "book_id": b.book_id,
            "title": b.title,
            "author": b.author,
            "available_copies": b.available_copies,
        }
        for b in db.query(Book).order_by(Book.book_id).all()
    ]


def _to_hits(db: Session, results: list[dict]) -> list[AIHit]:
    """Map [{book_id, reason}] onto real Book rows, silently dropping unknown ids."""
    by_id = {b.book_id: b for b in db.query(Book).all()}
    hits = []
    for r in results:
        book = by_id.get((r or {}).get("book_id"))
        if book:
            hits.append(
                AIHit(
                    book_id=book.book_id,
                    title=book.title,
                    author=book.author,
                    available_copies=book.available_copies,
                    reason=(r.get("reason") or "").strip(),
                )
            )
    return hits


@router.post("/search", response_model=AISearchResponse)
def ai_search(
    payload: AISearchRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    _require_ai()
    if not payload.query.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "query must not be empty")
    results = _run_ai(ai_service.semantic_search, payload.query, _books_payload(db))
    return AISearchResponse(query=payload.query, hits=_to_hits(db, results))


@router.get("/semantic-search", response_model=SemanticSearchResponse)
def ai_semantic_search(
    q: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Embedding-based search: rank books by cosine similarity to the query vector.

    Distinct from /ai/search (which is Gemini reasoning over the catalogue in one
    prompt). Books without a stored embedding are excluded, not errored.
    """
    _require_ai()
    if not q.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "q must not be empty")

    query_vec = _run_ai(embeddings_service.embed_text, q)

    candidates = []
    for book in db.query(Book).all():
        vec = embeddings_service.decode(book.embedding)
        if vec is None:
            logger.warning("Book %s has no embedding; excluded from semantic search.", book.book_id)
            continue
        candidates.append((book, vec))

    ranked = embeddings_service.rank(query_vec, candidates)[:5]
    hits = [
        SemanticHit(
            book_id=b.book_id,
            title=b.title,
            author=b.author,
            available_copies=b.available_copies,
            genre=b.genre,
            score=round(score, 4),
        )
        for b, score in ranked
    ]
    return SemanticSearchResponse(query=q, hits=hits)


@router.get("/recommend/{student_id}", response_model=AIRecommendResponse)
def ai_recommend(
    student_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    _require_ai()
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")

    borrowed = [
        (b.book_id, b.title)
        for b in db.query(Book)
        .join(BorrowRecord, BorrowRecord.book_pk == Book.id)
        .filter(BorrowRecord.student_pk == student.id)
        .all()
    ]
    results = _run_ai(ai_service.recommend, borrowed, _books_payload(db))

    borrowed_ids = {bid for bid, _ in borrowed}
    hits = [h for h in _to_hits(db, results) if h.book_id not in borrowed_ids]
    return AIRecommendResponse(student_id=student_id, recommendations=hits)


@router.post("/enrich", response_model=AIEnrichResponse)
def ai_enrich(
    payload: AIEnrichRequest,
    _=Depends(require_librarian),
):
    """Suggest genre / reading level / summary for a book. Librarian-only.

    Returns suggestions only — the librarian reviews them before saving the book.
    """
    _require_ai()
    if not payload.title.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "title must not be empty")
    meta = _run_ai(ai_service.enrich_book, payload.title, payload.author)
    return AIEnrichResponse(title=payload.title, author=payload.author, **meta)
