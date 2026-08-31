from django.core.cache import cache
from django.http import HttpResponse

ADMIN_LOGIN_MAX_ATTEMPTS = 5
ADMIN_LOGIN_WINDOW_SECONDS = 300  # 5 minutes


class AdminLoginRateLimitMiddleware:
    """
    Django's own /admin/login/ has no built-in brute-force protection —
    DRF's throttle_classes (used everywhere else in this project) only
    apply to DRF views, and this isn't one. Admin access is the most
    privileged level in this system (it can issue real GoSentePay
    refunds and edit wallet balances directly), so leaving its login
    page completely unguarded was a real gap, not a theoretical one.

    IP-based: N failed attempts within a window blocks further
    attempts from that IP, regardless of how many different passwords
    get tried against however many different usernames.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/admin/login/' and request.method == 'POST':
            ip = self._get_ip(request)
            cache_key = f'admin_login_attempts_{ip}'
            if cache.get(cache_key, 0) >= ADMIN_LOGIN_MAX_ATTEMPTS:
                return HttpResponse(
                    "Too many failed login attempts. Please try again later.",
                    status=429,
                )

        response = self.get_response(request)

        if request.path == '/admin/login/' and request.method == 'POST':
            ip = self._get_ip(request)
            cache_key = f'admin_login_attempts_{ip}'
            # Django admin's login view re-renders the same form with an
            # error (200) on failure, and redirects (302) on success —
            # there's no other simple hook into "did this attempt
            # actually succeed" without reimplementing the view itself.
            if response.status_code == 200:
                cache.set(cache_key, cache.get(cache_key, 0) + 1, ADMIN_LOGIN_WINDOW_SECONDS)
            elif response.status_code == 302:
                cache.delete(cache_key)

        return response

    def _get_ip(self, request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
