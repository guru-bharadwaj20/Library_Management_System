"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import ai, auth, books, borrow, students

# Create tables on startup. This is fine for dev and small deployments, but for
# real production use replace it with Alembic migrations so schema changes are
# versioned and reversible.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Library Management System API",
    description="Full-stack port of the original Tkinter library system.",
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


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
