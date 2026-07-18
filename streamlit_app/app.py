"""BiblioAI — Streamlit frontend (librarian/staff tooling).

Talks to the FastAPI backend over HTTP; the backend is the single source of
truth. Librarians get write actions (issue/return, add book/student, dashboard);
students get a read-only catalogue and their own borrowing view.
"""
import pandas as pd
import streamlit as st

import api_client as api

st.set_page_config(page_title="BiblioAI", page_icon="📚", layout="wide")


# --------------------------------------------------------------------------- #
# Session helpers
# --------------------------------------------------------------------------- #
def is_authenticated() -> bool:
    return bool(st.session_state.get("token"))


def is_librarian() -> bool:
    return st.session_state.get("role") == "librarian"


def logout():
    for key in ("token", "role", "username"):
        st.session_state.pop(key, None)


# --------------------------------------------------------------------------- #
# Login screen
# --------------------------------------------------------------------------- #
def login_screen():
    st.title("📚 BiblioAI")
    st.caption("Staff console — FastAPI + SQLAlchemy backend. (Students use the web app at /app.)")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        ok, payload = api.login(username, password)
        if ok:
            st.session_state.token = payload["access_token"]
            st.session_state.role = payload["role"]
            st.session_state.username = payload["username"]
            st.rerun()
        else:
            st.error(payload)

    st.info("First run? Seed the backend (`python -m app.seed_data`) to create the "
            "librarian account, then sign in with those printed credentials.")


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def dashboard_tab():
    st.subheader("Overview")
    ok_b, books = api.list_books()
    ok_s, students = api.list_students()
    if not ok_b:
        st.error(books)
        return
    if not ok_s:
        st.error(students)
        return

    total_titles = len(books)
    total_copies = sum(b["total_copies"] for b in books)
    available = sum(b["available_copies"] for b in books)
    on_loan = total_copies - available
    active_borrowers = sum(1 for s in students if s["borrowed_book_ids"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Titles", total_titles)
    c2.metric("Total copies", total_copies)
    c3.metric("Available", available)
    c4.metric("On loan", on_loan)
    c5.metric("Active borrowers", active_borrowers)

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("**Availability by title**")
        if books:
            df = pd.DataFrame(books)[["title", "available_copies", "total_copies"]]
            df = df.set_index("title")
            st.bar_chart(df)
    with right:
        st.markdown("**Out-of-stock titles**")
        out = [b for b in books if b["available_copies"] == 0]
        if out:
            st.dataframe(
                pd.DataFrame(out)[["book_id", "title", "author"]],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.success("Everything is in stock. 🎉")


# --------------------------------------------------------------------------- #
# Books
# --------------------------------------------------------------------------- #
def books_tab():
    st.subheader("Book catalogue")
    query = st.text_input("Search by title or author", key="book_search")
    ok, books = api.list_books(query or None)
    if not ok:
        st.error(books)
        return

    if books:
        df = pd.DataFrame(books)[
            ["book_id", "title", "author", "genre", "available_copies", "total_copies"]
        ]
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("No matching books.")

    if is_librarian():
        _add_book_form()


# Keys used by the add-book form, so we can clear them after a successful add.
_ADD_KEYS = [
    "add_book_id", "add_title", "add_author",
    "add_genre", "add_reading_level", "add_summary",
]


def _add_book_form():
    with st.expander("➕ Add a new book"):
        # Clear the fields on the run *after* a successful add (safe: before widgets exist).
        if st.session_state.pop("_book_added", False):
            for k in _ADD_KEYS:
                st.session_state.pop(k, None)

        c1, c2 = st.columns(2)
        book_id = c1.text_input("Book ID (e.g. B007)", key="add_book_id")
        title = c2.text_input("Title", key="add_title")
        author = st.text_input("Author", key="add_author")

        # AI auto-fill (Gemini) — populates the fields below for the librarian to review.
        if st.button("✨ Suggest genre, level & summary with AI"):
            if not title.strip():
                st.info("Enter a title first.")
            else:
                with st.spinner("Asking Gemini…"):
                    ok, payload = api.ai_enrich(title, author)
                if ok:
                    st.session_state["add_genre"] = payload["genre"]
                    st.session_state["add_reading_level"] = payload["reading_level"]
                    st.session_state["add_summary"] = payload["summary"]
                    st.rerun()
                else:
                    st.error(payload)

        c3, c4, c5 = st.columns([2, 2, 1])
        genre = c3.text_input("Genre", key="add_genre")
        reading_level = c4.text_input("Reading level", key="add_reading_level")
        copies = c5.number_input("Copies", min_value=0, value=1, step=1, key="add_copies")
        summary = st.text_area("Summary", key="add_summary")

        if st.button("Add book", type="primary"):
            ok, payload = api.add_book(
                book_id, title, author, int(copies),
                genre=genre or None, reading_level=reading_level or None,
                summary=summary or None,
            )
            if ok:
                st.success(f"Added '{payload['title']}'.")
                st.session_state["_book_added"] = True
                st.rerun()
            else:
                st.error(payload)


# --------------------------------------------------------------------------- #
# Students
# --------------------------------------------------------------------------- #
def students_tab():
    st.subheader("Students")
    query = st.text_input("Search by name", key="student_search")
    ok, students = api.list_students(query or None)
    if not ok:
        st.error(students)
        return

    if students:
        rows = [
            {
                "student_id": s["student_id"],
                "name": s["name"],
                "books_out": len(s["borrowed_book_ids"]),
                "borrowed": ", ".join(s["borrowed_book_ids"]) or "—",
            }
            for s in students
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("No matching students.")

    st.markdown("**Borrowing history**")
    hist_id = st.text_input("Enter a Student ID to view full history", key="hist_id")
    if hist_id:
        ok, records = api.borrow_history(hist_id)
        if not ok:
            st.error(records)
        elif records:
            df = pd.DataFrame(records)[
                ["book_id", "title", "issue_date", "due_date", "return_date", "penalty"]
            ]
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No borrowing history for this student.")

    if is_librarian():
        with st.expander("➕ Add a new student"):
            with st.form("add_student_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                student_id = col1.text_input("Student ID (e.g. S005)")
                name = col2.text_input("Name")
                if st.form_submit_button("Add student"):
                    ok, payload = api.add_student(student_id, name)
                    if ok:
                        st.success(f"Added '{payload['name']}'.")
                        st.rerun()
                    else:
                        st.error(payload)


# --------------------------------------------------------------------------- #
# Circulation (librarian only)
# --------------------------------------------------------------------------- #
def circulation_tab():
    st.subheader("Circulation")
    issue_col, return_col = st.columns(2)

    with issue_col:
        st.markdown("### 📤 Issue a book")
        with st.form("issue_form", clear_on_submit=True):
            book_id = st.text_input("Book ID", key="issue_book")
            student_id = st.text_input("Student ID", key="issue_student")
            if st.form_submit_button("Issue", use_container_width=True):
                ok, payload = api.issue_book(book_id, student_id)
                if ok:
                    st.success(payload["message"])
                    st.caption(f"Due: {payload['due_date']}")
                else:
                    st.error(payload)

    with return_col:
        st.markdown("### 📥 Return a book")
        with st.form("return_form", clear_on_submit=True):
            book_id = st.text_input("Book ID", key="return_book")
            student_id = st.text_input("Student ID", key="return_student")
            if st.form_submit_button("Return", use_container_width=True):
                ok, payload = api.return_book(book_id, student_id)
                if ok:
                    st.success(payload["message"])
                    if payload["penalty"] > 0:
                        st.metric("Penalty", f"${payload['penalty']:.2f}")
                else:
                    st.error(payload)


# --------------------------------------------------------------------------- #
# AI Librarian
# --------------------------------------------------------------------------- #
def _render_hits(hits):
    for h in hits:
        with st.container(border=True):
            st.markdown(f"**{h['title']}** — {h['author']}  \n`{h['book_id']}`")
            st.caption(f"💬 {h['reason']}")
            if h["available_copies"] > 0:
                st.success(f"{h['available_copies']} available", icon="✅")
            else:
                st.warning("Currently out of stock", icon="⛔")


def _render_semantic_hits(hits):
    for h in hits:
        with st.container(border=True):
            st.markdown(f"**{h['title']}** — {h['author']}  \n`{h['book_id']}`")
            meta = f"📐 similarity {h['score']:.3f}"
            if h.get("genre"):
                meta += f"  ·  {h['genre']}"
            st.caption(meta)
            if h["available_copies"] > 0:
                st.success(f"{h['available_copies']} available", icon="✅")
            else:
                st.warning("Currently out of stock", icon="⛔")


def ai_tab():
    st.subheader("🤖 AI Librarian")
    st.caption(
        "Powered by Google Gemini. (Requires GEMINI_API_KEY on the backend.)"
    )

    st.markdown("### Find a book")
    mode = st.radio(
        "Search technique",
        ["AI Search (LLM reasoning)", "Semantic Search (embeddings)"],
        horizontal=True,
        key="ai_mode",
    )

    if mode.startswith("AI Search"):
        st.caption("Gemini reads the whole catalogue and reasons about your request in one prompt.")
        query = st.text_input(
            "Describe what you're looking for",
            placeholder="e.g. a short dystopian novel about surveillance",
            key="ai_query",
        )
        if st.button("Search", type="primary", key="ai_search_btn"):
            if not query.strip():
                st.info("Type what you're after first.")
            else:
                with st.spinner("Asking the AI librarian…"):
                    ok, payload = api.ai_search(query)
                if not ok:
                    st.error(payload)
                elif payload["hits"]:
                    _render_hits(payload["hits"])
                else:
                    st.info("No good matches — try rephrasing.")
    else:
        st.caption(
            "Your query and each book are turned into embedding vectors; results are "
            "ranked by cosine similarity. (Backfill first: `python -m app.seed_embeddings`.)"
        )
        query = st.text_input(
            "Describe what you're looking for",
            placeholder="e.g. surveillance and lost freedom",
            key="sem_query",
        )
        if st.button("Search", type="primary", key="sem_search_btn"):
            if not query.strip():
                st.info("Type what you're after first.")
            else:
                with st.spinner("Embedding and ranking…"):
                    ok, payload = api.semantic_search(query)
                if not ok:
                    st.error(payload)
                elif payload["hits"]:
                    _render_semantic_hits(payload["hits"])
                else:
                    st.info("No embedded books to search. Run the backfill script, then retry.")

    st.divider()
    st.markdown("### Recommend for a reader")
    student_id = st.text_input("Student ID", placeholder="e.g. S001", key="ai_rec_student")
    if st.button("Recommend books"):
        if not student_id.strip():
            st.info("Enter a Student ID first.")
        else:
            with st.spinner("Finding personalized picks…"):
                ok, payload = api.ai_recommend(student_id.strip())
            if not ok:
                st.error(payload)
            elif payload["recommendations"]:
                _render_hits(payload["recommendations"])
            else:
                st.info("No recommendations yet — this reader may have no borrow history.")


# --------------------------------------------------------------------------- #
# Analytics (librarian only)
# --------------------------------------------------------------------------- #
def analytics_tab():
    st.subheader("📊 Circulation analytics")
    st.caption("Computed from full borrowing history (BorrowRecord), not just live counts.")
    ok, data = api.analytics_summary()
    if not ok:
        st.error(data)
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total loans (all time)", data["total_loans"])
    c2.metric("Active loans", data["active_loans"])
    c3.metric("Overdue now", data["overdue_count"])
    c4.metric("Penalty revenue", f"${data['total_penalty_revenue']:.2f}")

    avg = data["avg_loan_duration_days"]
    st.metric("Average loan duration", f"{avg:.1f} days" if avg is not None else "—")

    st.divider()
    st.markdown("**Most-borrowed titles**")
    mb = data["most_borrowed"]
    if mb:
        chart_df = pd.DataFrame(mb)[["title", "count"]].set_index("title")
        st.bar_chart(chart_df)
        st.dataframe(
            pd.DataFrame(mb)[["book_id", "title", "count"]],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No circulation history yet — issue and return some books first.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    if not is_authenticated():
        login_screen()
        return

    with st.sidebar:
        st.markdown(f"### 📚 BiblioAI\nSigned in as **{st.session_state.get('username')}**")
        st.caption(f"Role: {st.session_state.get('role')}")
        if st.button("Log out", use_container_width=True):
            logout()
            st.rerun()

    st.title("BiblioAI")

    if is_librarian():
        tabs = st.tabs(
            ["📊 Dashboard", "📖 Books", "🎓 Students", "🔄 Circulation",
             "🤖 AI Librarian", "📈 Analytics"]
        )
        with tabs[0]:
            dashboard_tab()
        with tabs[1]:
            books_tab()
        with tabs[2]:
            students_tab()
        with tabs[3]:
            circulation_tab()
        with tabs[4]:
            ai_tab()
        with tabs[5]:
            analytics_tab()
    else:
        tabs = st.tabs(["📖 Books", "🎓 Students", "🤖 AI Librarian"])
        with tabs[0]:
            books_tab()
        with tabs[1]:
            students_tab()
        with tabs[2]:
            ai_tab()


if __name__ == "__main__":
    main()
