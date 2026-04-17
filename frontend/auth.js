// auth.js — No-auth version with persistent unique user ID

function getOrCreateUserId() {
  let userId = localStorage.getItem("user_id");
  if (!userId) {
    userId = "user_" + Math.random().toString(36).substr(2, 9) + "_" + Date.now();
    localStorage.setItem("user_id", userId);
  }
  return userId;
}

function getCurrentUserEmail() {
  return localStorage.getItem("user_email") || "Guest";
}

function isLoggedIn() {
  return true;
}

async function apiFetch(path, options = {}) {
  const res = await fetch(CONFIG.API_URL + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    console.error("API error:", res.status, errBody);
    return null;
  }
  return res.json();
}