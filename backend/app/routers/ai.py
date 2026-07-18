"""AI-powered endpoints: natural-language search and personalized recommendations.

Both degrade gracefully: if no ANTHROPIC_API_KEY is configured they return 503,
so the rest of the system works without AI. Every book_id the model returns is
validated against the live catalogue before being sent back to the client.
"""
import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import ai_service
from ..database import get_db
from ..deps import get_current_user
from ..models import Book, BorrowRecord, Student
from ..schemas import AIHit, AIRecommendResponse, AISearchRequest, AISearchResponse

router = APIRouter(prefix="/ai", tags=["ai"])


def _require_ai():
    if not ai_service.is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI features are not configured. Set ANTHROPIC_API_KEY in the backend .env.",
        )


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
    try:
        results = ai_service.semantic_search(payload.query, _books_payload(db))
    except anthropic.APIError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"AI request failed: {exc}")
    except (ValueError, KeyError):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "AI returned an unparseable response; try rephrasing.",
        )
    return AISearchResponse(query=payload.query, hits=_to_hits(db, results))


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
    try:
        results = ai_service.recommend(borrowed, _books_payload(db))
    except anthropic.APIError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"AI request failed: {exc}")
    except (ValueError, KeyError):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "AI returned an unparseable response."
        )

    borrowed_ids = {bid for bid, _ in borrowed}
    hits = [h for h in _to_hits(db, results) if h.book_id not in borrowed_ids]
    return AIRecommendResponse(student_id=student_id, recommendations=hits)
