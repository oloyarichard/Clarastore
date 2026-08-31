function isLoggedIn() {
  // This is a UI convenience only, never a security boundary — the
  // real access token is HttpOnly and invisible to this code entirely.
  // The actual enforcement always happens server-side against that
  // cookie; this just decides which nav links to show.
  return !!getCookie('user_role');
}

function getRole() {
  return getCookie('user_role');
}

function isAgent() {
  return getRole() === 'agent';
}

/** Redirects to login if signed out, preserving the page to return to. */
function requireAuth() {
  if (!isLoggedIn()) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = '/login/?next=' + next;
  }
}

function requireAgent() {
  requireAuth();
  if (!isAgent()) {
    window.location.href = '/shop/';
  }
}

async function login(email, password) {
  // The login response sets the real (HttpOnly) and UI-companion
  // cookies itself — nothing here needs to store anything manually.
  await apiFetch('/auth/login/', { method: 'POST', body: { email, password }, auth: false });
  const profile = await apiFetch('/auth/profile/');
  await mergeGuestCart();
  return profile;
}

async function register(payload) {
  await apiFetch('/auth/register/', { method: 'POST', body: payload, auth: false });
  // Registration doesn't log the user in on the backend: log in right
  // after so the flow feels seamless, same as the Flutter app.
  return login(payload.email, payload.password);
}

/**
 * Merges whatever the guest added to their cart before signing in. No
 * session key needs to be passed: the backend reads it from the session
 * cookie the browser already sent along with this same request.
 */
async function mergeGuestCart() {
  try {
    await apiFetch('/cart/merge/', { method: 'POST', body: {} });
  } catch (e) {
    // Non-fatal: worst case the guest's pre-signup cart is empty or lost,
    // login itself still succeeds.
  }
}

function logout() {
  clearAuth();
  window.location.href = '/login/';
}

async function getCurrentUser() {
  if (!isLoggedIn()) return null;
  return apiFetch('/auth/profile/');
}
