"""Circulation — the core logic ported from Librarian.issue_book / return_book.

Unlike the original Tkinter version (which returned message strings for every
outcome), business-rule violations here surface as proper HTTP status codes:
404 when a book/student doesn't exist, 400 when a rule is broken.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_librarian
from ..models import Book, BorrowRecord, Student
from ..schemas import BorrowRequest, IssueResponse, ReturnResponse

router = APIRouter(prefix="/borrow", tags=["borrow"])


def _get_book(db: Session, book_id: str) -> Book:
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    return book


def _get_student(db: Session, student_id: str) -> Student:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return student


@router.post("/issue", response_model=IssueResponse)
def issue(
    payload: BorrowRequest,
    db: Session = Depends(get_db),
    _=Depends(require_librarian),
):
    book = _get_book(db, payload.book_id)
    student = _get_student(db, payload.student_id)

    if book.available_copies <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Book is not available")

    active_loans = (
        db.query(BorrowRecord)
        .filter(
            BorrowRecord.student_pk == student.id,
            BorrowRecord.return_date.is_(None),
        )
        .count()
    )
    if active_loans >= settings.borrow_limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Student has reached the borrowing limit ({settings.borrow_limit})",
        )

    now = datetime.utcnow()
    record = BorrowRecord(
        book_pk=book.id,
        student_pk=student.id,
        issue_date=now,
        due_date=BorrowRecord.compute_due_date(now),
    )
    book.available_copies -= 1
    db.add(record)
    db.commit()

    return IssueResponse(
        message=f"Book '{book.title}' issued to {student.name}.",
        due_date=record.due_date,
        book_id=book.book_id,
        student_id=student.student_id,
    )


@router.post("/return", response_model=ReturnResponse)
def return_book(
    payload: BorrowRequest,
    db: Session = Depends(get_db),
    _=Depends(require_librarian),
):
    book = _get_book(db, payload.book_id)
    student = _get_student(db, payload.student_id)

    record = (
        db.query(BorrowRecord)
        .filter(
            BorrowRecord.book_pk == book.id,
            BorrowRecord.student_pk == student.id,
            BorrowRecord.return_date.is_(None),
        )
        .first()
    )
    if not record:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This book was not borrowed by the student",
        )

    now = datetime.utcnow()
    record.return_date = now
    record.penalty = record.compute_penalty(now)
    book.available_copies += 1
    db.commit()

    if record.penalty > 0:
        message = f"Book '{book.title}' returned. Penalty: ${record.penalty:.2f}."
    else:
        message = f"Book '{book.title}' returned. No penalty."

    return ReturnResponse(
        message=message,
        penalty=record.penalty,
        book_id=book.book_id,
        student_id=student.student_id,
    )
