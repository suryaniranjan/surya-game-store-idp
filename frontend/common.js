// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type === 'error' ? ' error' : '');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Mark active nav link based on current page ────────────────────────────────
function setActiveNav() {
  const page = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.remove('active');
    if (l.dataset.page === page) l.classList.add('active');
  });
}

// ── Game image helpers ────────────────────────────────────────────────────────
function gameImageHTML(g) {
  if (g.image_url) {
    return `<div class="game-img-wrap">
      <img src="${g.image_url}" alt="${g.title}"
           onerror="this.parentElement.innerHTML=placeholderHTML()"/>
    </div>`;
  }
  return `<div class="game-img-wrap">${placeholderHTML()}</div>`;
}
function placeholderHTML() {
  return `<div class="game-img-placeholder">
    <div class="ph-icon">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5">
        <rect x="3" y="3" width="18" height="18" rx="3"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <path d="M21 15l-5-5L5 21"/>
      </svg>
    </div>
    <span>No Image</span>
  </div>`;
}

document.addEventListener('DOMContentLoaded', setActiveNav);