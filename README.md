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

Python_GUI/  → the original Tkinter app (kept for reference / provenance)
my_app/      → the original React prototype (kept for reference)
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
- Original **Tkinter GUI** and **React** prototype retained to show the evolution.

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

## ✅ Important Takeaways

- Practiced full-stack design by converting a Python GUI application into an interactive React website.
- Learned to handle CSV data in a React application using `papaparse`.
- Gained experience in creating a responsive user interface with modern CSS and React components.
- Aligned front-end design with back-end logic by replicating the original Python GUI workflow on the web.

---

## 📂 Project Overview

<div align="center">

<table>
  <tr>
    <td align="center" width="350">
      <img src="https://img.icons8.com/color/100/000000/python.png" width="60" alt="Python Logo"><br/>
      <strong>Tkinter GUI Platform</strong><br/>
      <p>A Python Tkinter-based desktop app for managing library inventory and student checkouts.</p>
    </td>
    <td align="center" width="350">
      <img src="https://img.icons8.com/color/100/000000/react-native.png" width="60" alt="React Logo"><br/>
      <strong>React Webpage</strong><br/>
      <p>A responsive website using React replicating the GUI app for browser-based access.</p>
    </td>
  </tr>
</table>

</div>

---

## 🛠️ Setup Instructions

### 🔹 For GUI Version
1. Navigate to the `Python_GUI` project directory.
2. Ensure you have Python 3 and Tkinter installed.
3. Run `codes.py` using a Python IDE or terminal: `python codes.py`.
4. Make sure the `.csv` files are in the same directory.

### 🔹 For Web Version
1. Navigate to the `my_app` folder.
2. Install the required dependencies: `npm install`.
3. Start the development server: `npm run dev`.
4. Open the provided URL in your preferred browser.

---

## 📌 Disclaimer

This dual-version library management system was developed for academic and portfolio purposes. **Redistributing or presenting this project as your own is strictly prohibited.**