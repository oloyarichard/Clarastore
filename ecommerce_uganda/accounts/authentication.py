from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Reads the access token from an httpOnly cookie instead of the
    Authorization header — the header is still checked first and used
    if present, so the Flutter app (which can't use browser cookies at
    all, and stores its tokens in flutter_secure_storage instead) keeps
    working exactly as before, unchanged.

    A cookie gets attached by the browser automatically on every
    request, same-site or not — unlike a Bearer header, which a
    malicious cross-site request has no way to forge. That's exactly
    the CSRF exposure cookie-based auth introduces, so this enforces a
    CSRF check on any unsafe-method request authenticated this way,
    mirroring what DRF's own SessionAuthentication does for the same
    reason.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        self.enforce_csrf(request)
        return user, validated_token

    def enforce_csrf(self, request):
        check = CSRFCheck(lambda req: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')
