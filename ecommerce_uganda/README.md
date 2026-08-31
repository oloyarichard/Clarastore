# Uganda Shop — Backend + Website (combined)

This Django project now serves **both** the REST API (used by the Flutter
app) **and** the full website (`webapp` app) — homepage, shop, cart,
checkout, wallet, orders, agent tools, and policy pages — from a single
process on one port.

## Running it

```bash
pip install -r requirements.txt --break-system-packages
# set up your .env with DB credentials (see settings.py for the full list)
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py collectstatic --noinput   # only needed when DEBUG=False
python3 manage.py runserver 8000
```

Then visit `http://localhost:8000/` — that's the whole site: homepage,
shop, cart, wallet, agent tools, everything. The API lives alongside it
under `/api/...` (e.g. `/api/products/`).

**Before real customers browse it:** create at least one `District` (via
`/admin/`) so signup's district dropdown isn't empty, and add some
`Product` entries so the shop isn't blank.

## What changed from running it as two separate servers

- **No CORS needed for the website anymore.** Since the site and the API
  are now served from the same origin, the browser never makes a
  cross-origin request for any of the pages under `/`. `CORS_ALLOWED_ORIGINS`
  in settings is still there and still matters for *other* clients hitting
  the API from a different origin (the Flutter app on web, a separately
  hosted admin tool, etc.) — just no longer required for this website to work.
- **Static files are managed by Django** now (`webapp/static/webapp/...`),
  served automatically in `DEBUG=True`, and collected to `STATIC_ROOT` via
  `collectstatic` for production (behind nginx/whitenoise/whatever you use).
- **URLs are clean paths**, not `.html` files or query-string IDs —
  `/product/14/`, `/orders/32/`, etc. — routed through Django's URLconf
  (`webapp/urls.py`) rather than a static file server.
- **`window.API_BASE_URL` is now just `/api`** (relative) — same value
  works in dev, staging, and production without per-environment config.

## App structure

- `accounts`, `catalog`, `orders`, `wallets` — the REST API (unchanged)
- `webapp` — the website: `views.py` (mostly simple `TemplateView`s),
  `urls.py`, `templates/webapp/` (one `base.html` + 17 pages extending
  it), `static/webapp/` (shared CSS/JS, generated from the standalone
  site build)

## The standalone site vs. this

The separately-deployable static site (`ecommerce_uganda_website/`, if
you still have it) still works as its own thing — useful if you ever want
to host the marketing/policy pages on a different domain/CDN than the
Django app itself, or split the storefront onto a separate service later.
This combined version is the simpler path for most cases: one thing to
run, one thing to deploy, no CORS to keep in sync.
