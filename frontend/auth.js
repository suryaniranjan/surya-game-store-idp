// ═══════════════════════════════════════════════════════════════
//  GameVault — Frontend Auth System (vanilla JS, no backend)
// ═══════════════════════════════════════════════════════════════

const USERS = [
  { username: "user",  password: "user@123",  role: "user",  display: "Player One" },
  { username: "surya", password: "surya@123", role: "user",  display: "Player Two" },
  { username: "admin", password: "admin123",  role: "admin", display: "Admin"      },
];

// ── Page access rules ────────────────────────────────────────────
const PAGE_ACCESS = {
  "index.html":    ["user"],
  "cart.html":     ["user"],
  "wishlist.html": ["user"],
  "orders.html":   ["user"],
  "payment.html":  ["user"],
  "admin.html":    ["admin"],
};

// ── Auth helpers ─────────────────────────────────────────────────
function authLogin(username, password) {
  const u = USERS.find(u => u.username === username && u.password === password);
  if (!u) return null;
  localStorage.setItem("gv_role",     u.role);
  localStorage.setItem("gv_username", u.username);
  localStorage.setItem("gv_display",  u.display);
  return u;
}

function authLogout() {
  localStorage.removeItem("gv_role");
  localStorage.removeItem("gv_username");
  localStorage.removeItem("gv_display");
  window.location.href = "login.html";
}

function getRole()        { return localStorage.getItem("gv_role"); }
function getUsername()    { return localStorage.getItem("gv_username"); }
function getDisplayName() { return localStorage.getItem("gv_display"); }
function isLoggedIn()     { return !!getRole(); }
function isAdmin()        { return getRole() === "admin"; }
function isUser()         { return getRole() === "user"; }

// ── Route guard ──────────────────────────────────────────────────
function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = "login.html";
    return false;
  }
  const page = window.location.pathname.split("/").pop() || "index.html";
  const allowed = PAGE_ACCESS[page];
  if (allowed && !allowed.includes(getRole())) {
    window.location.href = isAdmin() ? "admin.html" : "index.html";
    return false;
  }
  return true;
}

// ── Nav builder ──────────────────────────────────────────────────
function buildNav() {
  const role = getRole();
  const page = window.location.pathname.split("/").pop() || "index.html";

  // 1. Remove ANY stray sign-out buttons / nav-user-chip / nav-admin-right
  //    that may be hard-coded in the static HTML of any page.
  document.querySelectorAll(
    ".nav-signout-btn, .nav-user-chip, .nav-admin-right, .nav-admin-badge"
  ).forEach(el => el.remove());

  // 2. Build the single Sign Out button
  const signOutBtn = `
    <button type="button" class="nav-signout-btn" onclick="authLogout()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <polyline points="16 17 21 12 16 7"/>
        <line x1="21" y1="12" x2="9" y2="12"/>
      </svg>
      Sign Out
    </button>`;

  // 3. Inject nav links + Sign Out into .nav-links
  const navLinks = document.querySelector(".nav-links");
  if (!navLinks) return;

  if (role === "admin") {
    navLinks.innerHTML = `
      <a class="nav-link ${page === 'admin.html' ? 'active' : ''}" href="admin.html">⚙️ Dashboard</a>
      ${signOutBtn}`;
  } else {
    navLinks.innerHTML = `
      <a class="nav-link ${page === 'index.html'    ? 'active' : ''}" href="index.html">🎮 Store</a>
      <a class="nav-link ${page === 'cart.html'     ? 'active' : ''}" href="cart.html">🛒 Cart</a>
      <a class="nav-link ${page === 'wishlist.html' ? 'active' : ''}" href="wishlist.html">❤️ Wishlist</a>
      <a class="nav-link ${page === 'orders.html'   ? 'active' : ''}" href="orders.html">📦 Orders</a>
      ${signOutBtn}`;
  }
}

// ── userId helper ────────────────────────────────────────────────
function getOrCreateUserId() {
  const username = getUsername();
  if (username) return username;
  let id = localStorage.getItem("gv_anon_id");
  if (!id) {
    id = "anon_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("gv_anon_id", id);
  }
  return id;
}

// ── Auto-run ─────────────────────────────────────────────────────
(function () {
  const page = window.location.pathname.split("/").pop() || "index.html";
  if (page === "login.html") return;
  requireAuth();
  document.addEventListener("DOMContentLoaded", buildNav);
})();