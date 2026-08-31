// Same-origin deployment: Django serves both this frontend and the API,
// so a relative path works everywhere (dev, staging, production) without
// needing a config file per environment. Override window.API_BASE_URL
// before this script loads if you ever split them onto different hosts.
window.API_BASE_URL = window.API_BASE_URL || '/api';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function extractErrorMessage(data) {
  if (!data) return null;
  if (data.error) return data.error;
  if (data.detail) return data.detail;
  const firstKey = Object.keys(data)[0];
  if (firstKey && Array.isArray(data[firstKey]) && data[firstKey].length) {
    return `${firstKey}: ${data[firstKey][0]}`;
  }
  return null;
}

/**
 * Reads any plain (non-HttpOnly) cookie by name — used for the small
 * UI-only companions (user_role, user_id) the backend sets alongside
 * the real, HttpOnly access/refresh token cookies. Those two never
 * appear here and can't be read by JS at all, by design: this only
 * ever sees the cookies that were deliberately made readable.
 */
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Clears the UI-only cookies immediately (so the nav updates without
 * waiting on a network round-trip), then asks the backend to clear the
 * real HttpOnly cookies — JS has no way to delete those itself.
 */
function clearAuth() {
  document.cookie = 'user_role=; Max-Age=0; path=/';
  document.cookie = 'user_id=; Max-Age=0; path=/';
  fetch(window.API_BASE_URL + '/auth/logout/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'X-CSRFToken': getCsrfToken() || '' },
  }).catch(() => { /* best-effort — the cookies expire on their own regardless */ });
}

/**
 * Reads the `csrftoken` cookie Django sets (see base.html's {% csrf_token %}).
 * Not HttpOnly by design: Django's CSRF scheme relies on JS being able to
 * read this value and echo it back as a header, proving the request came
 * from a page that could read the site's own cookies (same-origin).
 */
function getCsrfToken() {
  return getCookie('csrftoken');
}

const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS'];

async function tryRefresh() {
  // No refresh token to read or send here — it lives in an HttpOnly
  // cookie the browser attaches on its own. A successful response sets
  // a fresh access_token cookie the same way; there's nothing for this
  // function to store manually anymore.
  try {
    const resp = await fetch(window.API_BASE_URL + '/auth/refresh/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() || '' },
      body: JSON.stringify({}),
    });
    return resp.ok;
  } catch (e) {
    return false;
  }
}

/**
 * Core request helper used by every page. The access token itself is
 * never read or attached here — it lives in an HttpOnly cookie the
 * browser sends automatically on every request via `credentials:
 * 'include'`, which is also what lets a guest's cart persist across
 * requests without any JS needing to see that cookie directly.
 * `auth: false` now only controls whether a 401 triggers a
 * refresh-and-retry — public endpoints don't need that dance even if a
 * stale cookie happens to be present.
 */
async function apiFetch(path, { method = 'GET', body, auth = true, retry = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };

  if (!SAFE_METHODS.includes(method.toUpperCase())) {
    const csrfToken = getCsrfToken();
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
  }

  let resp;
  try {
    resp = await fetch(window.API_BASE_URL + path, {
      method,
      headers,
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0, null);
  }

  if (resp.status === 401 && retry && auth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return apiFetch(path, { method, body, auth, retry: false });
    }
    clearAuth();
    throw new ApiError('Your session expired: please log in again.', 401, null);
  }

  const text = await resp.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch (e) { data = null; }
  }

  if (!resp.ok) {
    throw new ApiError(extractErrorMessage(data) || 'Something went wrong. Please try again.', resp.status, data);
  }

  return data;
}
