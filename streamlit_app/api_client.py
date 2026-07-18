"""Thin HTTP client around the FastAPI backend.

The JWT lives in ``st.session_state`` (per-browser-session, in memory) and is
attached to every request. Each call returns ``(ok, payload)`` where ``payload``
is parsed JSON on success or a human-readable error string on failure.
"""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

TIMEOUT = 15


def _headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _request(method: str, path: str, **kwargs):
    try:
        resp = requests.request(
            method, f"{API_URL}{path}", headers=_headers(), timeout=TIMEOUT, **kwargs
        )
    except requests.RequestException as exc:
        return False, f"Cannot reach the API at {API_URL}. Is the backend running? ({exc})"

    if resp.ok:
        if resp.content:
            return True, resp.json()
        return True, None

    # Try to surface FastAPI's {"detail": ...} message.
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = resp.text
    if isinstance(detail, list):  # pydantic validation errors
        detail = "; ".join(d.get("msg", str(d)) for d in detail)
    return False, detail or f"Request failed ({resp.status_code})"


# ---- Auth ----
def login(username: str, password: str):
    # OAuth2PasswordRequestForm expects form-encoded data, not JSON.
    return _request("POST", "/auth/login", data={"username": username, "password": password})


# ---- Books ----
def list_books(q: str | None = None):
    return _request("GET", "/books", params={"q": q} if q else None)


def add_book(book_id, title, author, total_copies):
    return _request(
        "POST",
        "/books",
        json={"book_id": book_id, "title": title, "author": author, "total_copies": total_copies},
    )


# ---- Students ----
def list_students(q: str | None = None):
    return _request("GET", "/students", params={"q": q} if q else None)


def add_student(student_id, name):
    return _request("POST", "/students", json={"student_id": student_id, "name": name})


def borrow_history(student_id: str):
    return _request("GET", f"/students/{student_id}/borrowed")


# ---- Circulation ----
def issue_book(book_id, student_id):
    return _request("POST", "/borrow/issue", json={"book_id": book_id, "student_id": student_id})


def return_book(book_id, student_id):
    return _request("POST", "/borrow/return", json={"book_id": book_id, "student_id": student_id})
