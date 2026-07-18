"""Book catalogue: search/list (any user) and add (librarian only)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_librarian
from ..models import Book
from ..schemas import BookCreate, BookOut

router = APIRouter(prefix="/books", tags=["books"])


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
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book
