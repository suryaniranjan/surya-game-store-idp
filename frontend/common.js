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

// ── API fetch helper ──────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(CONFIG.API_URL + path, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.message || `Error ${res.status}`, 'error');
      return null;
    }
    return await res.json();
  } catch (e) {
    toast('Network error — please try again', 'error');
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════════
//  WISHLIST HELPERS  (shared across index.html & wishlist.html)
// ═══════════════════════════════════════════════════════════════════

// In-memory set of wishlisted game_ids for instant UI feedback
let _wishlistIds = new Set();

/** Fetch the user's wishlist once on page load and populate _wishlistIds */
async function loadWishlistIds(userId) {
  const data = await apiFetch(`/wishlist/${userId}`);
  if (data && data.items) {
    _wishlistIds = new Set(data.items.map(i => i.game_id));
  }
  return _wishlistIds;
}

/** Walk all .wish-btn elements and set their filled/outline state */
function syncHeartButtons() {
  document.querySelectorAll('.wish-btn').forEach(btn => {
    const gid        = btn.dataset.gameId;
    const wishlisted = _wishlistIds.has(gid);
    btn.classList.toggle('wishlisted', wishlisted);
    btn.title     = wishlisted ? 'Remove from Wishlist' : 'Add to Wishlist';
    btn.innerHTML = wishlisted ? '♥' : '♡';
  });
}

/**
 * Toggle a game in/out of the wishlist.
 * Called by the ♡ button rendered on each game card in index.html.
 *
 * @param {object} game   — full game object from the API
 * @param {string} userId — current user id
 */
async function toggleWishlist(game, userId) {
  const alreadyWishlisted = _wishlistIds.has(game.game_id);

  // Optimistic update — flip the heart immediately
  if (alreadyWishlisted) {
    _wishlistIds.delete(game.game_id);
  } else {
    _wishlistIds.add(game.game_id);
  }
  syncHeartButtons();

  if (alreadyWishlisted) {
    // Remove from wishlist
    const data = await apiFetch(`/wishlist/${userId}/items/${game.game_id}`, {
      method: 'DELETE'
    });
    if (data) {
      toast(`💔 "${game.title}" removed from wishlist`);
    } else {
      // Roll back on failure
      _wishlistIds.add(game.game_id);
      syncHeartButtons();
    }
  } else {
    // Add to wishlist
    const data = await apiFetch(`/wishlist/${userId}/items`, {
      method: 'POST',
      body: JSON.stringify({
        game_id:   game.game_id,
        title:     game.title,
        price:     game.price,
        image_url: game.image_url || '',
        genre:     game.genre     || '',
        platform:  game.platform  || '',
        stock:     game.stock     ?? 0
      })
    });
    if (data) {
      toast(`❤️ "${game.title}" added to wishlist`);
    } else {
      // Roll back on failure
      _wishlistIds.delete(game.game_id);
      syncHeartButtons();
    }
  }
}
