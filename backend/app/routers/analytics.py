"""Circulation analytics computed from BorrowRecord history (librarian-only)."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_librarian
from ..models import Book, BorrowRecord
from ..schemas import AnalyticsSummary, MostBorrowed

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: Session = Depends(get_db), _=Depends(require_librarian)):
    # Most-borrowed titles (top 5 by total loan count).
    rows = (
        db.query(Book.book_id, Book.title, func.count(BorrowRecord.id).label("cnt"))
        .join(BorrowRecord, BorrowRecord.book_pk == Book.id)
        .group_by(Book.id)
        .order_by(func.count(BorrowRecord.id).desc())
        .limit(5)
        .all()
    )
    most_borrowed = [MostBorrowed(book_id=r[0], title=r[1], count=r[2]) for r in rows]

    total_penalty = db.query(func.coalesce(func.sum(BorrowRecord.penalty), 0.0)).scalar() or 0.0
    total_loans = db.query(func.count(BorrowRecord.id)).scalar() or 0
    active_loans = (
        db.query(func.count(BorrowRecord.id))
        .filter(BorrowRecord.return_date.is_(None))
        .scalar()
        or 0
    )
    overdue_count = (
        db.query(func.count(BorrowRecord.id))
        .filter(BorrowRecord.return_date.is_(None), BorrowRecord.due_date < datetime.utcnow())
        .scalar()
        or 0
    )

    # Average loan duration (returned records only), computed in Python to stay
    # backend-agnostic — SQLite has no clean date-diff function.
    returned = (
        db.query(BorrowRecord.issue_date, BorrowRecord.return_date)
        .filter(BorrowRecord.return_date.isnot(None))
        .all()
    )
    if returned:
        days = [(rd - idt).total_seconds() / 86400 for idt, rd in returned]
        avg_loan_duration_days = round(sum(days) / len(days), 2)
    else:
        avg_loan_duration_days = None

    return AnalyticsSummary(
        most_borrowed=most_borrowed,
        total_penalty_revenue=round(float(total_penalty), 2),
        active_loans=active_loans,
        total_loans=total_loans,
        overdue_count=overdue_count,
        avg_loan_duration_days=avg_loan_duration_days,
    )
