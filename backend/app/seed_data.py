"""Seed the database from the repo's existing CSV files + create a librarian.

Run from the ``backend/`` directory:

    python -m app.seed_data

Idempotent: books/students are only inserted when their tables are empty, and
the admin user is only created if it doesn't already exist.
"""
import csv
import secrets
from pathlib import Path

from .config import settings
from .database import Base, SessionLocal, engine
from .models import Book, Student, User
from .security import hash_password

# backend/app/seed_data.py -> parents[2] == repo root
REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_csv(name: str) -> Path | None:
    for candidate in (
        REPO_ROOT / name,
        REPO_ROOT / "Python_GUI" / name,
        REPO_ROOT / "my_app" / "public" / name,
    ):
        if candidate.exists():
            return candidate
    return None


def _seed_books(db) -> int:
    if db.query(Book).count() > 0:
        return 0
    path = _find_csv("books.csv")
    if not path:
        print("books.csv not found — skipping book seed.")
        return 0
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 4 and row[0].strip():
                copies = int(row[3])
                db.add(
                    Book(
                        book_id=row[0].strip(),
                        title=row[1].strip(),
                        author=row[2].strip(),
                        total_copies=copies,
                        available_copies=copies,
                    )
                )
                count += 1
    return count


def _seed_students(db) -> int:
    if db.query(Student).count() > 0:
        return 0
    path = _find_csv("students.csv")
    if not path:
        print("students.csv not found — skipping student seed.")
        return 0
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip():
                db.add(Student(student_id=row[0].strip(), name=row[1].strip()))
                count += 1
    return count


def _seed_admin(db) -> None:
    if db.query(User).filter(User.username == settings.admin_username).first():
        print(f"Librarian '{settings.admin_username}' already exists — skipping.")
        return
    password = settings.admin_password or secrets.token_urlsafe(12)
    db.add(
        User(
            username=settings.admin_username,
            hashed_password=hash_password(password),
            role="librarian",
        )
    )
    if not settings.admin_password:
        print(
            "\n=== Generated librarian credentials (store these now) ===\n"
            f"  username: {settings.admin_username}\n"
            f"  password: {password}\n"
            "  This password is not saved anywhere else.\n"
        )


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        n_books = _seed_books(db)
        n_students = _seed_students(db)
        _seed_admin(db)
        db.commit()
        print(f"Seed complete. Added {n_books} books, {n_students} students.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
