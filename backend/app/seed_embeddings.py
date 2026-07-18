"""Backfill semantic-search embeddings for every book.

Run from the ``backend/`` directory:

    python -m app.seed_embeddings          # only books without an embedding
    python -m app.seed_embeddings --force  # recompute all (e.g. after edits)

Idempotent by default: books that already have an embedding are skipped unless
``--force`` is passed. Requires GEMINI_API_KEY; without it, nothing is computed.
"""
import sys

from . import embeddings_service
from .database import Base, SessionLocal, engine
from .models import Book


def backfill(force: bool = False) -> None:
    if not embeddings_service.is_configured():
        print("GEMINI_API_KEY not set — cannot compute embeddings. Skipping.")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        books = db.query(Book).all()
        computed = skipped = failed = 0
        for book in books:
            if book.embedding and not force:
                skipped += 1
                continue
            text = embeddings_service.book_embedding_text(
                book.title, book.author, book.genre, book.summary
            )
            try:
                book.embedding = embeddings_service.encode(embeddings_service.embed_text(text))
                computed += 1
            except Exception as exc:  # noqa: BLE001 — report and continue
                print(f"  ! {book.book_id} ({book.title}): {exc}")
                failed += 1
        db.commit()
        print(
            f"Embeddings backfill complete: {computed} computed, "
            f"{skipped} skipped, {failed} failed."
        )
    finally:
        db.close()


if __name__ == "__main__":
    backfill(force="--force" in sys.argv)
