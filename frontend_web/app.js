/* ===== Library Management System — customer web frontend =====
   Vanilla JS SPA. Talks to the FastAPI backend on the same origin
   (mounted at /app, API routes live at the origin root: /auth, /books, /ai...). */

const app = document.getElementById("app");

// ---------- helpers ----------
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const token = () => sessionStorage.getItem("token");
const setSession = (t, username, name) => {
  sessionStorage.setItem("token", t);
  sessionStorage.setItem("username", username);
  if (name) sessionStorage.setItem("name", name);
};
const clearSession = () => ["token", "username", "name"].forEach((k) => sessionStorage.removeItem(k));

async function api(method, path, { json, form } = {}) {
  const headers = {};
  if (token()) headers["Authorization"] = "Bearer " + token();
  let body;
  if (json) { headers["Content-Type"] = "application/json"; body = JSON.stringify(json); }
  if (form) body = new URLSearchParams(form);
  const res = await fetch(path, { method, headers, body });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    let detail = (data && data.detail) || res.statusText;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg || d).join("; ");
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

const go = (hash) => { location.hash = hash; };

// ---------- shared chrome ----------
const BRAND = `📚 Library<span class="accent"> System</span>`;

function navPublic() {
  return `
  <nav class="nav">
    <div class="brand" onclick="location.hash=''">${BRAND}</div>
    <div class="nav-actions">
      <a class="btn btn-link" href="#login">Sign In</a>
      <a class="btn btn-primary btn-sm" href="#register">Register</a>
    </div>
  </nav>`;
}

function navAuthed() {
  const name = sessionStorage.getItem("name") || sessionStorage.getItem("username") || "reader";
  return `
  <nav class="nav">
    <div class="brand" onclick="location.hash='#dashboard'">${BRAND}</div>
    <div class="nav-actions">
      <span class="userchip">Signed in as <b>${esc(name)}</b></span>
      <button class="btn btn-ghost btn-sm" id="logout">Log out</button>
    </div>
  </nav>`;
}

function footer() {
  return `
  <footer>
    <div class="container">
      <div class="footer-grid">
        <div>
          <div class="brand">${BRAND}</div>
          <p class="footer-desc">Your campus library companion — browse the catalogue,
            search in plain English or by meaning, and get personalized reading recommendations.</p>
        </div>
        <div>
          <h4>Quick Links</h4>
          <ul class="footer-links">
            <li><a href="#">Home</a></li>
            <li><a href="#login">Sign In</a></li>
            <li><a href="#register">Register</a></li>
          </ul>
        </div>
        <div>
          <h4>Features</h4>
          <ul class="footer-links">
            <li>📖 Catalogue</li>
            <li>🤖 AI Search</li>
            <li>🧭 Semantic Search</li>
            <li>⭐ Recommendations</li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© 2026 Library Management System.</span>
        <span>FastAPI · SQLAlchemy · Google Gemini</span>
      </div>
    </div>
  </footer>`;
}

// ---------- views ----------
function landing() {
  app.innerHTML = `
    ${navPublic()}
    <section class="hero">
      <div class="container">
        <h1>Library <span class="accent">Management System</span></h1>
        <p>Your all-in-one campus library companion for browsing the catalogue,
           AI-powered search, and personalized reading recommendations.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="#login">Sign In →</a>
          <a class="btn btn-ghost" href="#register">Create Account</a>
        </div>
      </div>
    </section>
    <section class="container">
      <div class="features">
        <div class="feature">
          <div class="icon">🤖</div>
          <h3>AI Librarian</h3>
          <p>Ask for a book in plain English — Gemini reads the catalogue and reasons about your request.</p>
        </div>
        <div class="feature">
          <div class="icon">🧭</div>
          <h3>Semantic Search</h3>
          <p>Find books by meaning using embedding vectors ranked by cosine similarity.</p>
        </div>
        <div class="feature">
          <div class="icon">⭐</div>
          <h3>Recommendations</h3>
          <p>Personalized picks generated from a reader's borrowing history.</p>
        </div>
      </div>
    </section>
    ${footer()}`;
}

function loginView() {
  app.innerHTML = `
    ${navPublic()}
    <div class="auth-wrap">
      <div class="auth-card">
        <div class="brand">${BRAND}</div>
        <p class="auth-sub">Sign in to your account</p>
        <div id="msg"></div>
        <form id="loginForm">
          <div class="field">
            <label>Username</label>
            <input name="username" placeholder="Your login username" autocomplete="username" required />
          </div>
          <div class="field">
            <label>Password</label>
            <input name="password" type="password" placeholder="Enter your password" autocomplete="current-password" required />
          </div>
          <button class="btn btn-primary btn-block" type="submit">Sign In →</button>
        </form>
        <p class="auth-foot">Don't have an account? <a href="#register">Register here</a></p>
      </div>
    </div>`;

  document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const btn = f.querySelector("button");
    btn.disabled = true; btn.textContent = "Signing in…";
    try {
      const data = await api("POST", "/auth/login", {
        form: { username: f.username.value.trim(), password: f.password.value },
      });
      setSession(data.access_token, data.username);
      go("#dashboard");
    } catch (err) {
      showMsg("error", err.message);
      btn.disabled = false; btn.textContent = "Sign In →";
    }
  });
}

function registerView() {
  app.innerHTML = `
    ${navPublic()}
    <div class="auth-wrap">
      <div class="auth-card">
        <div class="brand">Join ${BRAND}</div>
        <p class="auth-sub">Create your reader account</p>
        <div id="msg"></div>
        <form id="regForm">
          <div class="field">
            <label>Full Name <span class="opt">(optional)</span></label>
            <input name="name" placeholder="Enter your full name" />
          </div>
          <div class="field">
            <label>Username <span class="hint">(your login ID)</span></label>
            <input name="username" placeholder="e.g. reader_jane" autocomplete="username" required />
          </div>
          <div class="field">
            <label>Password <span class="hint">(min 6 characters)</span></label>
            <input name="password" type="password" placeholder="Choose a password" autocomplete="new-password" required />
          </div>
          <button class="btn btn-primary btn-block" type="submit">Create Account →</button>
        </form>
        <p class="auth-foot">Already have an account? <a href="#login">Sign in</a></p>
      </div>
    </div>`;

  document.getElementById("regForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const username = f.username.value.trim();
    const password = f.password.value;
    const name = f.name.value.trim();
    if (username.length < 3) return showMsg("error", "Username must be at least 3 characters.");
    if (password.length < 6) return showMsg("error", "Password must be at least 6 characters.");
    const btn = f.querySelector("button");
    btn.disabled = true; btn.textContent = "Creating…";
    try {
      await api("POST", "/auth/register", { json: { username, password } });
      // auto sign-in after registration
      const data = await api("POST", "/auth/login", { form: { username, password } });
      setSession(data.access_token, data.username, name);
      go("#dashboard");
    } catch (err) {
      showMsg("error", err.message);
      btn.disabled = false; btn.textContent = "Create Account →";
    }
  });
}

// ---------- dashboard ----------
let dashState = { mode: "browse" };

function dashboardView() {
  if (!token()) return go("#login");
  app.innerHTML = `
    ${navAuthed()}
    <div class="dash">
      <div class="container">
        <h2>Catalogue</h2>
        <p class="sub">Browse the collection, or search with AI.</p>

        <div class="segmented" id="modes">
          <button class="seg" data-mode="browse">📖 Browse</button>
          <button class="seg" data-mode="ai">🤖 AI Search</button>
          <button class="seg" data-mode="semantic">🧭 Semantic Search</button>
        </div>
        <div class="seg-hint" id="segHint"></div>

        <div class="searchbar">
          <input id="q" placeholder="Search…" />
          <button class="btn btn-primary" id="searchBtn">Search</button>
        </div>

        <div id="results"><div class="spinner">Loading catalogue…</div></div>

        <div class="panel">
          <h3>⭐ Recommendations</h3>
          <p class="sub">Personalized picks from a reader's borrowing history. Try a seeded reader ID such as <b>S001</b>.</p>
          <div class="row">
            <input id="readerId" placeholder="Reader ID (e.g. S001)" />
            <button class="btn btn-ghost" id="recBtn">Recommend</button>
          </div>
          <div id="recResults"></div>
        </div>
      </div>
    </div>
    ${footer()}`;

  document.getElementById("logout").addEventListener("click", () => { clearSession(); go(""); });

  document.querySelectorAll("#modes .seg").forEach((b) =>
    b.addEventListener("click", () => setMode(b.dataset.mode)));
  document.getElementById("searchBtn").addEventListener("click", runSearch);
  document.getElementById("q").addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
  document.getElementById("recBtn").addEventListener("click", runRecommend);
  document.getElementById("readerId").addEventListener("keydown", (e) => { if (e.key === "Enter") runRecommend(); });

  setMode(dashState.mode);
  runSearch(); // initial load (browse, empty query -> all books)
}

const HINTS = {
  browse: "Filter the catalogue by title or author.",
  ai: "Gemini reads the whole catalogue and reasons about your request in one prompt.",
  semantic: "Your query and each book are embedded; results are ranked by cosine similarity.",
};
const PLACEHOLDERS = {
  browse: "Search by title or author…",
  ai: "e.g. a short dystopian novel about surveillance",
  semantic: "e.g. surveillance and the loss of personal freedom",
};

function setMode(mode) {
  dashState.mode = mode;
  document.querySelectorAll("#modes .seg").forEach((b) =>
    b.classList.toggle("active", b.dataset.mode === mode));
  document.getElementById("segHint").textContent = HINTS[mode];
  document.getElementById("q").placeholder = PLACEHOLDERS[mode];
}

function bookCard(b, extra = "") {
  const avail = b.available_copies > 0
    ? `<span class="badge ok">✓ ${b.available_copies} available</span>`
    : `<span class="badge no">Out of stock</span>`;
  const genre = b.genre ? `<div class="meta">${esc(b.genre)}</div>` : "";
  return `
    <div class="book">
      <div class="title">${esc(b.title)}</div>
      <div class="author">${esc(b.author || "Unknown")}</div>
      <div class="id">${esc(b.book_id)}</div>
      ${genre}
      ${extra}
      <div>${avail}</div>
    </div>`;
}

async function runSearch() {
  const q = document.getElementById("q").value.trim();
  const box = document.getElementById("results");
  box.innerHTML = `<div class="spinner">Searching…</div>`;
  try {
    let cards = "";
    if (dashState.mode === "browse") {
      const books = await api("GET", "/books" + (q ? `?q=${encodeURIComponent(q)}` : ""));
      if (!books.length) return (box.innerHTML = `<div class="empty">No matching books.</div>`);
      cards = books.map((b) => bookCard(b)).join("");
    } else if (dashState.mode === "ai") {
      if (!q) return (box.innerHTML = `<div class="empty">Describe what you're looking for.</div>`);
      const data = await api("POST", "/ai/search", { json: { query: q } });
      if (!data.hits.length) return (box.innerHTML = `<div class="empty">No good matches — try rephrasing.</div>`);
      cards = data.hits.map((h) => bookCard(h, `<div class="reason">💬 ${esc(h.reason)}</div>`)).join("");
    } else {
      if (!q) return (box.innerHTML = `<div class="empty">Describe what you're looking for.</div>`);
      const data = await api("GET", "/ai/semantic-search?q=" + encodeURIComponent(q));
      if (!data.hits.length) return (box.innerHTML = `<div class="empty">No embedded books to search yet.</div>`);
      cards = data.hits.map((h) =>
        bookCard(h, `<div><span class="badge score">📐 similarity ${h.score.toFixed(3)}</span></div>`)).join("");
    }
    box.innerHTML = `<div class="grid">${cards}</div>`;
  } catch (err) {
    box.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
  }
}

async function runRecommend() {
  const id = document.getElementById("readerId").value.trim();
  const box = document.getElementById("recResults");
  if (!id) { box.innerHTML = `<div class="empty">Enter a reader ID first.</div>`; return; }
  box.innerHTML = `<div class="spinner">Finding personalized picks…</div>`;
  try {
    const data = await api("GET", "/ai/recommend/" + encodeURIComponent(id));
    if (!data.recommendations.length)
      return (box.innerHTML = `<div class="empty">No recommendations — this reader may have no borrowing history.</div>`);
    box.innerHTML = `<div class="grid" style="margin-top:16px">${
      data.recommendations.map((h) => bookCard(h, `<div class="reason">💬 ${esc(h.reason)}</div>`)).join("")
    }</div>`;
  } catch (err) {
    box.innerHTML = `<div class="alert alert-error" style="margin-top:16px">${esc(err.message)}</div>`;
  }
}

// ---------- misc ----------
function showMsg(kind, text) {
  const el = document.getElementById("msg");
  if (el) el.innerHTML = `<div class="alert alert-${kind === "error" ? "error" : "ok"}">${esc(text)}</div>`;
}

// ---------- router ----------
function router() {
  const h = location.hash;
  if (h === "#login") return loginView();
  if (h === "#register") return registerView();
  if (h === "#dashboard") return dashboardView();
  return landing();
}
window.addEventListener("hashchange", router);
router();
