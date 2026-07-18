# Library Management System

What began as a single-file **Tkinter desktop app** backed by CSV files is now a
**full-stack application**: a FastAPI + SQLAlchemy REST API with JWT auth and
role-based access, a Streamlit frontend, and an **AI librarian assistant** powered
by Google Gemini (natural-language search, embedding-based semantic search,
recommendations, and metadata enrichment).

It runs **locally on SQLite by design** — this is a portfolio/learning project,
not a hosted service. See [Known limitations](#-known-limitations) for the
tradeoffs that choice implies.

---

## 🧭 Architecture

```
┌──────────────────┐        HTTP/JSON        ┌────────────────────────────┐
│  streamlit_app/  │  ───────────────────▶   │          backend/          │
│  Streamlit UI    │   JWT Bearer token      │     FastAPI + SQLAlchemy    │
│  (thin client)   │  ◀───────────────────   │  auth · books · students · │
└──────────────────┘                         │  borrow · ai · analytics   │
                                             └───────┬───────────┬────────┘
                                                     │           │
                                   ┌─────────────────▼──┐   ┌────▼──────────────┐
                                   │  SQLite (local)     │   │  Google Gemini    │
                                   │  users · books ·    │   │  chat + embeddings│
                                   │  students ·         │   │  (optional; 503   │
                                   │  borrow_records     │   │  without a key)   │
                                   └─────────────────────┘   └───────────────────┘
```

### Repository layout

```
backend/
  ├── app/
  │   ├── config.py            pydantic-settings (env / .env)
  │   ├── database.py          SQLAlchemy engine + session
  │   ├── models.py            User · Book · Student · BorrowRecord
  │   ├── schemas.py           Pydantic request/response contracts
  │   ├── security.py          bcrypt hashing + JWT
  │   ├── deps.py              auth / require_librarian dependencies
  │   ├── ai_service.py        Gemini chat (search, recommend, enrich)
  │   ├── embeddings_service.py Gemini embeddings + cosine similarity
  │   ├── seed_data.py         seed books/students + create librarian
  │   ├── seed_embeddings.py   backfill book embeddings
  │   └── routers/             auth · books · students · borrow · ai · analytics
  └── seed/                    canonical seed CSVs (books, students)
streamlit_app/                 Streamlit UI — a pure API client
legacy/
  └── tkinter_app/             the original Tkinter + CSV app, kept for provenance
```

## 🚀 Features

- **FastAPI backend** — REST API, automatic OpenAPI docs, JWT auth, librarian vs.
  student roles.
- **Relational persistence** — `borrow_records` is the full circulation history
  (it replaced the original `logs.csv`); the backend is the single source of truth.
- **Fixed penalty bug** — the original computed the due date as *today − grace
  period* (always penalising); the ported logic correctly uses *issue date +
  grace period*.
- **Two AI search techniques** (Google Gemini), kept side by side to show the
  contrast:
  - **AI Search (LLM reasoning)** — Gemini reasons over the whole catalogue in one prompt.
  - **Semantic Search (embeddings)** — books and the query are embedded; results
    ranked by cosine similarity, computed locally in Python (no vector DB).
- **AI recommendations** — personalized picks from a reader's borrow history.
- **AI metadata enrichment** — one-click genre / reading level / summary when
  adding a book (librarian reviews before saving).
- **Circulation analytics** — most-borrowed titles, penalty revenue, active vs.
  historical loans, overdue count, average loan duration — from real history.
- **Graceful AI degradation** — with no `GEMINI_API_KEY`, all AI endpoints return
  **503** and the rest of the system is unaffected.
- **Streamlit frontend** — role-aware UI: dashboard, catalogue, circulation, AI
  Librarian, and analytics tabs.
- Original **Tkinter GUI** retained under `legacy/` to show the evolution.

## ⚡ Quick start

```bash
# 1. Backend
cd backend && python -m venv .venv && .venv\Scripts\activate   # (Windows)
pip install -r requirements.txt
cp .env.example .env                 # add GEMINI_API_KEY to enable AI (optional)
python -m app.seed_data              # seeds data + prints librarian credentials
python -m app.seed_embeddings        # backfill book embeddings (needs GEMINI_API_KEY)
uvicorn app.main:app --reload        # API at http://localhost:8000/docs

# 2. Frontend (new terminal)
cd streamlit_app && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # API_URL=http://localhost:8000
streamlit run app.py                 # UI at http://localhost:8501
```

See [backend/README.md](backend/README.md) and
[streamlit_app/README.md](streamlit_app/README.md) for the full env-var list and
per-component details.

---

## ✅ What this project demonstrates

- Designing a **REST API** with FastAPI: routing, dependency injection, OpenAPI docs.
- **Relational data modelling** with SQLAlchemy.
- **Auth & authorization** — JWT tokens, bcrypt hashing, role-based access control.
- **Two LLM integration patterns** — direct prompting vs. embeddings + cosine
  similarity — plus disciplined guardrails (validate model output against the DB,
  degrade to 503, fail-soft so the provider can never 500 an endpoint).
- Porting real domain logic from a legacy app, **fixing a bug** in the process.
- A clean **client/server split**: the Streamlit UI holds no business logic.

---

## ⚠️ Known limitations

Honest tradeoffs, made deliberately for a local portfolio project:

- **SQLite, single-writer.** Fine for one user on one machine. It would not handle
  concurrent writers (issue/return from multiple clients at once) — that would need
  Postgres and row-level locking. `DATABASE_URL` is routed through SQLAlchemy, so a
  swap is *possible*, but it's out of scope and untested here.
- **Schema via `create_all`, not migrations.** New columns (e.g. `embedding`) appear
  only on a fresh database — after a model change, delete `library.db` and re-seed.
  A production system would use Alembic.
- **JWT lives in Streamlit `session_state` (in memory).** This avoids `localStorage`
  XSS token theft, but the token doesn't survive a hard browser refresh — you log in
  again. A "remember me" flow was intentionally not added.
- **Embeddings are computed on book creation and via the backfill script**, not on
  edit — there is no update-book endpoint, so an edited title/summary won't
  re-embed until `seed_embeddings.py --force` is run.
- **Semantic search loads all embeddings and ranks in Python.** Perfect for a
  catalogue of this size; for thousands of books this should move to a real vector
  index (e.g. `pgvector`).
- **AI output is non-deterministic and costs API calls.** All AI features are
  optional and degrade to 503 without a key.

---

## 📌 Disclaimer

This project was developed for academic and portfolio purposes. **Redistributing or presenting this project as your own is strictly prohibited.**
