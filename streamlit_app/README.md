# Library Management System — Frontend (Streamlit)

A Streamlit UI for the Library Management System. It is a **pure API client** —
all data and business rules live in the FastAPI backend; this app only renders
and calls endpoints.

## Features

- JWT login (token held in `st.session_state`, in memory)
- **Role-aware UI**: librarians get a dashboard, circulation (issue/return), and
  add-book / add-student forms; students get a read-only catalogue + history view
- Live metrics dashboard (titles, copies, on-loan, out-of-stock) with charts
- Book / student search and per-student borrowing history

## Local setup

Start the [backend](../backend/README.md) first, then:

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

## Deployment (Streamlit Community Cloud)

1. Push the repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), point at `streamlit_app/app.py`.
3. Add `API_URL` (your deployed backend URL) under **App settings → Secrets** or
   as an environment variable.
4. Make sure the backend's `CORS_ORIGINS` includes the Streamlit app URL.
