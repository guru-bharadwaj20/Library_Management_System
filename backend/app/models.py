"""ORM models.

``BorrowRecord`` replaces the old ``logs.csv`` and is the single source of
truth for who has what on loan.

NOTE on the penalty bug fix: the original codes.py computed
``due_date = today - GRACE_PERIOD``, which always lands in the past and so
always produced a penalty. The correct semantics — a book is due
``GRACE_PERIOD`` days *after* it is issued — live in ``compute_due_date``.
"""
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .config import settings
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="student")  # "student" | "librarian"
    created_at = Column(DateTime, default=datetime.utcnow)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    book_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False, default="")
    total_copies = Column(Integer, nullable=False, default=0)
    available_copies = Column(Integer, nullable=False, default=0)
    # AI-enriched metadata (nullable — populated on demand via /ai/enrich).
    genre = Column(String, nullable=True)
    reading_level = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    # Semantic-search embedding: a JSON-encoded list of floats (SQLite has no
    # vector type). Computed on book creation / backfill; NULL until then.
    embedding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    records = relationship("BorrowRecord", back_populates="book")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    student_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    records = relationship("BorrowRecord", back_populates="student")


class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True)
    book_pk = Column(Integer, ForeignKey("books.id"), nullable=False)
    student_pk = Column(Integer, ForeignKey("students.id"), nullable=False)
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)  # NULL == still on loan
    penalty = Column(Float, nullable=False, default=0.0)

    book = relationship("Book", back_populates="records")
    student = relationship("Student", back_populates="records")

    @staticmethod
    def compute_due_date(issue_date: datetime) -> datetime:
        """A book is due GRACE_PERIOD days after it is issued."""
        return issue_date + timedelta(days=settings.grace_period_days)

    def compute_penalty(self, return_date: datetime) -> float:
        """Penalty = late_days * rate, capped at MAX_PENALTY; 0 if returned on time."""
        late_days = (return_date.date() - self.due_date.date()).days
        if late_days <= 0:
            return 0.0
        return float(min(late_days * settings.base_penalty_rate, settings.max_penalty))
