"""Book catalogue: search/list (any user) and add (librarian only)."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import embeddings_service
from ..database import get_db
from ..deps import get_current_user, require_librarian
from ..models import Book
from ..schemas import BookCreate, BookOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


def _maybe_embed(db: Session, book: Book) -> None:
    """Compute and store a semantic-search embedding for a freshly-saved book.

    Best-effort: if the AI key is missing or the embedding call fails, the book
    is still created — it just won't appear in semantic search until backfilled.
    """
    if not embeddings_service.is_configured():
        return
    try:
        text = embeddings_service.book_embedding_text(
            book.title, book.author, book.genre, book.summary
        )
        book.embedding = embeddings_service.encode(embeddings_service.embed_text(text))
        db.commit()
    except Exception as exc:  # noqa: BLE001 — never fail a create over an optional embedding
        db.rollback()
        logger.warning("Could not embed book %s: %s", book.book_id, exc)


@router.get("", response_model=list[BookOut])
def list_books(
    q: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Book)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Book.title.ilike(like), Book.author.ilike(like)))
    return query.order_by(Book.book_id).all()


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def add_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    _=Depends(require_librarian),
):
    if db.query(Book).filter(Book.book_id == payload.book_id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "book_id already exists")
    book = Book(
        book_id=payload.book_id,
        title=payload.title,
        author=payload.author,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,
        genre=payload.genre,
        reading_level=payload.reading_level,
        summary=payload.summary,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    _maybe_embed(db, book)  # also covers the enrich-then-save flow (enriched fields are embedded)
    db.refresh(book)
    return book
