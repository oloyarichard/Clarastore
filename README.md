# Uganda E-commerce — Flutter App

## Setup

1. Install dependencies:
   ```
   flutter pub get
   ```

2. Point the app at your Django backend. The base URL is compiled in via
   a Dart define (see `lib/core/constants.dart`), so run with:
   ```
   flutter run --dart-define=API_BASE_URL=http://YOUR_BACKEND_HOST:8000/api
   ```
   - Android emulator → host machine's localhost is `10.0.2.2` (this is
     the default if you don't pass `--dart-define`)
   - iOS simulator → use `http://localhost:8000/api`
   - Physical device → use your machine's LAN IP, e.g. `http://192.168.1.50:8000/api`,
     and make sure the Django dev server is run with `runserver 0.0.0.0:8000`

3. The backend must have `django-cors-headers` configured to accept
   requests from the Flutter app if you're testing on web or a device on
   a different origin — this wasn't in the original backend scaffold, add
   it if you hit CORS errors testing on Flutter web.

## What's wired up

- Guest browsing + cart (no login needed) — cart persists via a cookie
  jar that mirrors Django's session cookie
- Checkout requires login, pays from wallet balance
- MTN MoMo / Airtel Money top-up with polling until the customer
  approves on their phone
- Role-based navigation: customers get the shop/cart/orders/wallet tabs,
  agents get dashboard/orders/wallet/profile tabs after login
- Agent order status updates (pick up, dispatch with transport reference,
  or mark delivered for hub-direct orders)
- Customer delivery confirmation ("Received" / "Not received")

## Running as a website (Flutter web)

Web support is already scaffolded in `web/` (manifest, icons, index.html
using the standard bootstrap placeholder). To run it:

```
flutter build web --dart-define=API_BASE_URL=https://your-backend-domain/api
```

The output lands in `build/web/` — deploy that folder to any static host.

If your Flutter SDK version doesn't recognize the `{{flutter_bootstrap_js}}`
placeholder in `web/index.html` (older SDKs use a different loader format),
run `flutter create --platforms=web .` once from the project root — it
regenerates `web/index.html` correctly for your installed version without
touching anything in `lib/`.

Since this build is a full single-page app, it pairs well with the separate
static marketing/policy site (`ecommerce_uganda_website/`) — that one handles
the homepage, download page, and legal pages, and links to this build for
the actual shopping experience.

## App launcher icon

The real Clarastore logo is already in `assets/icon/icon.png` (transparent)
and `assets/icon/icon_ios.png` (opaque, for iOS's no-transparency
requirement), with `flutter_launcher_icons` configured in `pubspec.yaml`
to generate real native icons from them. Since this project was hand-built
without running `flutter create`, there's no `android/`/`ios/` folder yet —
one-time setup:

```
flutter create .
flutter pub get
dart run flutter_launcher_icons
```

`flutter create .` adds the native platform folders without touching
anything in `lib/`; the launcher icons command then generates every
required icon size for Android, iOS, and web from the two source images
already in place. Re-run just the last command any time you swap the logo.

## Known gaps / next steps
- No image upload for products — that's an admin/Django-side task
- Agent order list doesn't yet distinguish "needs action" from
  "waiting on customer confirmation" visually — both just show status text
- Push notifications aren't wired up — order status changes require the
  app to poll (pull-to-refresh) rather than notifying in real time
- Could not run `flutter analyze` or `flutter pub get` in this environment
  (no Flutter SDK, and pub.dev isn't reachable) — the code was reviewed
  manually for structural correctness (brace/paren balance, import
  resolution, and every model field cross-checked against every screen
  that reads it) but hasn't been compiled. Run `flutter analyze` first
  thing after `pub get` to catch anything that slipped through.
