# Legacy — Tkinter desktop app (provenance)

This is the **original** Library Management System: a single-file Tkinter GUI
backed by CSV files. It is kept for reference to show where the project started
before it was rebuilt as a full-stack app (`backend/` + `streamlit_app/`).

It is **not** part of the live system and shares no data with it — the current
source of truth is the database behind the FastAPI backend.

## Run it standalone

```bash
cd legacy/tkinter_app
python codes.py
```

`books.csv` and `students.csv` here are a local snapshot so the app still runs on
its own. Note the original penalty bug (due date computed as *today − grace
period*) is preserved here on purpose; the corrected logic lives in the backend.
