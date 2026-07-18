"""FastAPI application entrypoint."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import ai, analytics, auth, books, borrow, students

# Static customer web frontend (repo_root/frontend_web), served by this backend.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend_web"

# Create tables on startup. This project targets a local, single-user SQLite
# database by design, so create_all is the right tool here — no migration
# framework is needed for the intended scope. (If the schema changes, delete
# library.db and re-seed.)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BiblioAI API",
    description="AI-powered campus library — catalogue, AI search, recommendations, and circulation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(students.router)
app.include_router(borrow.router)
app.include_router(ai.router)
app.include_router(analytics.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# Mounted last so API routes above take precedence. The customer site is at /app/.
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
