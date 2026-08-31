const ORDER_STATUS = {
  pending: { label: 'Pending', color: '#a99aa3', step: 0 },
  assigned: { label: 'Assigned to agent', color: '#8f7cff', step: 1 },
  picked_up: { label: 'Picked up', color: '#8f7cff', step: 2 },
  dispatched: { label: 'Dispatched', color: '#ff5c9a', step: 3 },
  awaiting_confirmation: { label: 'Awaiting your confirmation', color: '#e0a83e', step: 3 },
  delivered: { label: 'Delivered', color: '#20a879', step: 4 },
  flagged: { label: 'Flagged: under investigation', color: '#df5b68', step: -1 },
  lost: { label: 'Lost / Refunded', color: '#df5b68', step: -1 },
  cancelled: { label: 'Cancelled', color: '#a99aa3', step: -1 },
};

/**
 * The four real milestones every non-flagged order passes through. `step`
 * on ORDER_STATUS above maps a status to its position here, so the
 * timeline can highlight progress based on actual order state rather
 * than a decorative counter.
 */
const ORDER_TIMELINE_STEPS = ['Placed', 'Assigned', 'Picked up', 'On the way', 'Delivered'];

function orderTimelineHtml(status) {
  const meta = ORDER_STATUS[status];
  if (!meta || meta.step === -1) return '';
  return `<div class="order-timeline">${ORDER_TIMELINE_STEPS.map((label, i) => `
    <div class="timeline-step ${i <= meta.step ? 'done' : ''}">
      <span class="timeline-dot"></span>
      <span class="timeline-label">${label}</span>
    </div>`).join('')}</div>`;
}

function formatUGX(amount) {
  const n = Number(amount) || 0;
  return 'UGX ' + n.toLocaleString('en-UG', { maximumFractionDigits: 0 });
}

function formatDate(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) +
    ', ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function statusBadgeHtml(status) {
  const meta = ORDER_STATUS[status] || { label: status, color: '#9c9990' };
  return `<span class="status-badge" style="color:${meta.color};background:${meta.color}22;border-color:${meta.color}55;">${escapeHtml(meta.label)}</span>`;
}

/** Small toast in the corner: used instead of alert() for a nicer feel. */
function showToast(message, isError = false) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:200;display:flex;flex-direction:column;gap:10px;';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.textContent = message;
  toast.style.cssText = `
    background:${isError ? '#fff0f0' : '#ffffff'};
    border:1px solid ${isError ? '#f3b9bd' : '#eee3e9'};
    color:${isError ? '#c73e4a' : '#211b24'};
    padding:14px 18px; border-radius:14px; font-size:0.92rem; max-width:320px;
    font-family: 'DM Sans', sans-serif; font-weight: 500;
    box-shadow:0 14px 40px rgba(45,25,42,.14); animation:fadeIn 0.2s ease;
  `;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4500);
}

function showError(err) {
  showToast(err instanceof Error ? err.message : String(err), true);
}

/** Renders the auth-aware part of the header nav: call after DOM ready on every page. */
async function renderAuthNav() {
  const slot = document.getElementById('nav-auth-slot');
  const cartSlot = document.getElementById('nav-cart-slot');
  if (!slot) return;

  if (!isLoggedIn()) {
    slot.innerHTML = `<a href="/login/">Log in</a><a href="/signup/" class="btn btn-gold nav-cta">Sign up</a>`;
    if (cartSlot) cartSlot.style.display = '';
    return;
  }

  if (isAgent()) {
    slot.innerHTML = `
      <a href="/agent/dashboard/">Dashboard</a>
      <a href="/orders/">Deliveries</a>
      <a href="/wallet/">Wallet</a>
      <a href="/account/">Account</a>
      <a href="#" id="nav-logout" class="btn btn-outline nav-cta">Log out</a>
    `;
    if (cartSlot) cartSlot.style.display = 'none';
  } else {
    slot.innerHTML = `
      <a href="/orders/">Orders</a>
      <a href="/wallet/">Wallet</a>
      <a href="/account/">Account</a>
      <a href="#" id="nav-logout" class="btn btn-outline nav-cta">Log out</a>
    `;
    if (cartSlot) cartSlot.style.display = '';
  }

  const logoutLink = document.getElementById('nav-logout');
  if (logoutLink) {
    logoutLink.addEventListener('click', (e) => { e.preventDefault(); logout(); });
  }

  if (cartSlot && !isAgent()) {
    try {
      const cart = await apiFetch('/cart/');
      updateCartBadge(cart.count || 0);
    } catch (e) { /* not fatal */ }
  }
}

function updateCartBadge(count) {
  const badge = document.getElementById('cart-count');
  if (!badge) return;
  const changed = badge.textContent !== String(count);
  badge.textContent = count;
  badge.style.display = count > 0 ? 'inline-flex' : 'none';
  if (changed && count > 0) {
    badge.classList.remove('pop');
    // restart the animation even if it's already mid-play from a rapid update
    void badge.offsetWidth;
    badge.classList.add('pop');
  }
}

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

/** Clean line-art placeholder for a product with no image: replaces the
 * emoji glyph, which renders inconsistently (or as a blank box) across
 * different operating systems and browsers. */
function productPlaceholderIcon() {
  return '<svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4l4 2 4-2 4 3-3 3-1-1v9H8v-9l-1 1-3-3 4-3z"/></svg>';
}
