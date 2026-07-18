# Library Management System

A Library Management System that has grown from a single-file **Tkinter desktop app**
into a real, deployable **full-stack application**: a FastAPI + SQLAlchemy REST API
with JWT auth and role-based access, backed by a relational database, and a
Streamlit frontend.

---

## 🧭 Architecture

```
┌──────────────────┐        HTTP/JSON        ┌────────────────────────┐
│  streamlit_app/  │  ───────────────────▶   │       backend/         │
│  Streamlit UI    │   JWT Bearer token      │  FastAPI + SQLAlchemy  │
│  (API client)    │  ◀───────────────────   │  auth · books ·        │
└──────────────────┘                         │  students · borrow     │
                                             └───────────┬────────────┘
                                                         │
                                          ┌──────────────▼──────────────┐
                                          │  SQLite (dev) / Postgres     │
                                          │  users · books · students ·  │
                                          │  borrow_records              │
                                          └──────────────────────────────┘
```

### Repository layout

```
backend/           FastAPI + SQLAlchemy API (the source of truth)
  ├── app/         config · database · models · schemas · security · routers
  └── seed/        canonical seed CSVs (books, students)
streamlit_app/     Streamlit UI — a thin API client
legacy/
  └── tkinter_app/ the original Tkinter + CSV app, kept for provenance
```

## 🚀 Features

- **FastAPI backend** — REST API, OpenAPI docs, JWT auth, librarian vs. student roles.
- **Relational persistence** — `borrow_records` replaces the old `logs.csv`; the
  backend is the single source of truth (no more client-side CSV mutation that
  vanished on refresh).
- **Streamlit frontend** — role-aware UI with a live metrics dashboard, search,
  circulation, and per-student borrowing history.
- **Fixed penalty bug** — the original computed the due date as *today − grace
  period* (always penalising); the ported logic correctly uses *issue date +
  grace period*.
- **AI Librarian (Claude)** — natural-language catalogue search and personalized
  recommendations from borrow history; degrades gracefully to 503 without an API key.
- Original **Tkinter GUI** retained under `legacy/` to show the evolution.

## ⚡ Quick start

```bash
# 1. Backend
cd backend && python -m venv .venv && .venv\Scripts\activate   # (Windows)
pip install -r requirements.txt
cp .env.example .env
python -m app.seed_data          # seeds data + prints librarian credentials
uvicorn app.main:app --reload    # API at http://localhost:8000/docs

# 2. Frontend (new terminal)
cd streamlit_app && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py             # UI at http://localhost:8501
```

See [backend/README.md](backend/README.md) and
[streamlit_app/README.md](streamlit_app/README.md) for full setup and deployment
(Supabase / Render / Streamlit Cloud) notes.

---

## ✅ What this project demonstrates

- Designing a **REST API** with FastAPI: routing, dependency injection, OpenAPI docs.
- **Relational data modelling** with SQLAlchemy and a DB-agnostic config (SQLite ↔ Postgres).
- **Auth & authorization** — JWT tokens, bcrypt hashing, role-based access control.
- Porting real domain logic from a legacy app, **fixing a bug** in the process.
- A clean **client/server split**: the Streamlit UI holds no business logic.
- A story of **evolution** — from a single-file Tkinter script to a deployable service.

---

## 📌 Disclaimer

This project was developed for academic and portfolio purposes. **Redistributing or presenting this project as your own is strictly prohibited.**