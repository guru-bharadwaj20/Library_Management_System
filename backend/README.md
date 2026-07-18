# Library Management System — Backend (FastAPI)

REST API for the Library Management System. It ports the domain logic from the
original Tkinter app (`Python_GUI/codes.py`) into a proper service backed by a
relational database, JWT auth, and role-based access control.

## Stack

- **FastAPI** — API framework + automatic OpenAPI docs
- **SQLAlchemy 2.0** — ORM; swap SQLite (dev) ↔ Postgres (prod) via `DATABASE_URL` alone
- **PyJWT + bcrypt** — token auth and password hashing
- **pydantic-settings** — 12-factor config from env / `.env`

## Data model

| Table | Purpose |
|-------|---------|
| `users` | Auth accounts, `role` ∈ {`student`, `librarian`} |
| `books` | Catalogue with `total_copies` / `available_copies` |
| `students` | Library members (the `S001…` records) |
| `borrow_records` | One row per loan — **replaces the old `logs.csv`**. `return_date IS NULL` means still on loan. |

### Penalty logic (bug fix vs. the original)

The original `codes.py` computed `due_date = today − GRACE_PERIOD`, which always
lands in the past and therefore *always* charged a penalty. The corrected
semantics live in `BorrowRecord.compute_due_date`:

```
due_date  = issue_date + GRACE_PERIOD_DAYS
penalty   = min(late_days * BASE_PENALTY_RATE, MAX_PENALTY)   # 0 if returned on time
```

All four constants (`BORROW_LIMIT`, `GRACE_PERIOD_DAYS`, `BASE_PENALTY_RATE`,
`MAX_PENALTY`) are configurable via env vars.

## API surface

| Method & path | Access | Description |
|---------------|--------|-------------|
| `POST /auth/register` | public | Self-register a **student** account |
| `POST /auth/register-librarian` | librarian | Create another librarian |
| `POST /auth/login` | public | OAuth2 password flow → JWT |
| `GET /books?q=` | any user | List/search books |
| `POST /books` | librarian | Add a book |
| `GET /students?q=` | any user | List/search students (+ currently-held book IDs) |
| `POST /students` | librarian | Add a student |
| `GET /students/{id}/borrowed` | any user | Full borrow history |
| `POST /borrow/issue` | librarian | Issue a book (validates stock + borrow limit) |
| `POST /borrow/return` | librarian | Return a book, compute penalty |
| `POST /ai/search` | any user | Natural-language catalogue search (Claude) |
| `GET /ai/recommend/{id}` | any user | Personalized recommendations from borrow history (Claude) |
| `GET /health` | public | Liveness probe |

Interactive docs at `http://localhost:8000/docs`.

### AI features (Claude)

`/ai/search` and `/ai/recommend` call the Claude API. Set `ANTHROPIC_API_KEY` in
`.env` to enable them; without it they return **503** and the rest of the system
is unaffected. The backend validates every `book_id` the model returns against
the live catalogue, so hallucinated ids are dropped before reaching the client.
For a large catalogue, the inline-catalogue prompt should be replaced with an
embeddings + `pgvector` retrieval step so only top-K candidates are sent.

## Local setup

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit SECRET_KEY etc.
python -m app.seed_data       # seeds books/students from the repo CSVs + prints librarian creds
uvicorn app.main:app --reload
```

The seed script prints a generated librarian password **once** (unless you set
`ADMIN_PASSWORD` in `.env`). Save it — sign in with it from the Streamlit app.

## Deployment

### Database — Supabase (Postgres)

1. Create a project at [supabase.com](https://supabase.com).
2. **Project Settings → Database → Connection string → URI**. Copy it and set it
   as `DATABASE_URL`, e.g.
   `postgresql+psycopg2://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres`.
3. For serverless/edge hosts, use the **connection pooler** endpoint (port
   `6543`, "Transaction" mode) to avoid exhausting Postgres connections.

### API — Render or Railway

Set these environment variables on the service: `DATABASE_URL`, `SECRET_KEY`,
`CORS_ORIGINS` (include your Streamlit URL), and optionally `ADMIN_PASSWORD`.

- **Build command:** `pip install -r backend/requirements.txt`
- **Start command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

After the first deploy, run the seed once (Render/Railway shell):
`cd backend && python -m app.seed_data`.

> **Production note:** `Base.metadata.create_all()` on startup is fine for now,
> but before real production use replace it with **Alembic** migrations so schema
> changes are versioned and reversible.
