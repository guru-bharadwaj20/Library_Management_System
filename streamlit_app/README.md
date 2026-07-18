# Library Management System — Frontend (Streamlit)

A Streamlit UI for the Library Management System. It is a **pure API client** —
all data and business rules live in the FastAPI backend; this app only renders
and calls endpoints.

## Features

- JWT login (token held in `st.session_state`, in memory)
- **Role-aware UI**:
  - **Librarian** — Dashboard, Books (with an "✨ Suggest with AI" add-book flow),
    Students, Circulation (issue/return), AI Librarian, and Analytics tabs.
  - **Student** — read-only catalogue, student search/history, and AI Librarian.
- **AI Librarian tab** — toggle between *AI Search (LLM reasoning)* and
  *Semantic Search (embeddings, with similarity scores)*, plus per-reader
  recommendations.
- **Analytics tab** (librarian) — most-borrowed titles (bar chart), penalty
  revenue, active vs. historical loans, overdue count, average loan duration.

## Local setup

Start the [backend](../backend/README.md) first (including
`python -m app.seed_embeddings` if you want semantic search populated), then:

```bash
cd streamlit_app
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # API_URL=http://localhost:8000
streamlit run app.py
```

Open http://localhost:8501 and sign in with the librarian credentials printed by
the backend's `seed_data.py`.

## Configuration

| Var | Default | Purpose |
|-----|---------|---------|
| `API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

The AI Librarian and Analytics tabs simply call backend endpoints — if the backend
has no `GEMINI_API_KEY`, the AI features surface a clear "not configured" message
and the rest of the UI keeps working.
