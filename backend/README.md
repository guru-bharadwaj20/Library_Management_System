# BiblioAI — Backend (FastAPI)

REST API for **BiblioAI**. It ports the domain logic from the original Tkinter
app (`legacy/tkinter_app/codes.py`) into a proper service backed by a relational
database, JWT auth, and role-based access control, adds an optional AI layer
(Google Gemini), and serves the customer web app at `/app`.

Runs on a **local SQLite database by design** — see "Scope" below.

## Stack

- **FastAPI** — API framework + automatic OpenAPI docs
- **SQLAlchemy 2.0** — ORM over a local SQLite database
- **PyJWT + bcrypt** — token auth and password hashing
- **pydantic-settings** — config from env / `.env`
- **google-genai + numpy** — Gemini chat & embeddings; cosine similarity in Python

## Data model

| Table | Purpose |
|-------|---------|
| `users` | Auth accounts, `role` ∈ {`student`, `librarian`} |
| `books` | Catalogue: copies, AI metadata (`genre`/`reading_level`/`summary`), and a JSON `embedding` |
| `students` | Library members (the `S001…` records) |
| `borrow_records` | One row per loan — the full circulation history. `return_date IS NULL` means still on loan. |

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
| `POST /books` | librarian | Add a book (auto-computes its embedding) |
| `GET /students?q=` | any user | List/search students (+ currently-held book IDs) |
| `POST /students` | librarian | Add a student |
| `GET /students/{id}/borrowed` | any user | Full borrow history |
| `POST /borrow/issue` | librarian | Issue a book (validates stock + borrow limit) |
| `POST /borrow/return` | librarian | Return a book, compute penalty |
| `POST /ai/search` | any user | Natural-language search — Gemini reasons over the catalogue |
| `GET /ai/semantic-search?q=` | any user | Embedding search — cosine similarity, ranked in Python |
| `GET /ai/recommend/{id}` | any user | Personalized recommendations from borrow history |
| `POST /ai/enrich` | librarian | Suggest genre / reading level / summary for a book |
| `GET /analytics/summary` | librarian | Circulation analytics from BorrowRecord history |
| `GET /health` | public | Liveness probe |

Interactive docs at `http://localhost:8000/docs`.

### AI features (Google Gemini)

All `/ai/*` endpoints (and the embedding step of `POST /books`) call Gemini via the
`google-genai` SDK. Set `GEMINI_API_KEY` in `.env` to enable them; without it they
return **503** and the rest of the system is unaffected. Any provider failure is
caught and returned as a clean **502** — the AI layer can never crash an endpoint.

Two search techniques are provided deliberately:

- **`/ai/search`** — the whole catalogue goes into one prompt and Gemini reasons
  over it. Every `book_id` it returns is validated against the DB, so hallucinated
  ids are dropped.
- **`/ai/semantic-search`** — each book is embedded (`gemini-embedding-001`) and
  stored as a JSON float list in `Book.embedding`; the query is embedded and books
  ranked by cosine similarity (numpy). Books without an embedding are excluded, not
  errored. Embeddings are computed on `POST /books` and backfilled by
  `seed_embeddings.py`.

## Local setup

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # edit SECRET_KEY, add GEMINI_API_KEY (optional)
python -m app.seed_data            # seed books/students + create librarian
python -m app.seed_embeddings      # backfill embeddings (needs GEMINI_API_KEY; --force to recompute)
uvicorn app.main:app --reload
```

The seed script prints a generated librarian password **once** (unless you set
`ADMIN_PASSWORD` in `.env`). Save it — sign in with it from the Streamlit app.

> After changing a model column, delete `library.db` and re-run the seed steps —
> the schema is created with `create_all`, not migrations (intentional for this
> local scope).

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `DATABASE_URL` | `sqlite:///./library.db` | Local database (SQLite by design) |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — set a strong value |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | Token lifetime |
| `CORS_ORIGINS` | `http://localhost:8501,...` | Comma-separated allowed origins |
| `BORROW_LIMIT` / `GRACE_PERIOD_DAYS` / `BASE_PENALTY_RATE` / `MAX_PENALTY` | `5` / `2` / `1` / `50` | Circulation rules |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / *(blank)* | Seeded librarian (blank password → generated + printed) |
| `GEMINI_API_KEY` | *(blank)* | Enables AI features; blank → AI endpoints return 503 |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Chat model for search/recommend/enrich |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model for semantic search |

## Scope

This backend targets **local, single-user development on SQLite** — that is the
intended end state, not an interim step toward deployment. It is not hosted, does
not use Postgres, and does not need a migration framework at this scale. The known
tradeoffs of that choice are listed in the [root README](../README.md#-known-limitations).
