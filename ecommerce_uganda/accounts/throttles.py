from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Throttles login attempts by IP address, regardless of whether the
    credentials being tried are valid. This is what actually slows down
    a brute-force/credential-stuffing attempt — there was previously no
    friction here at all, meaning an attacker could try passwords as
    fast as their connection allowed.
    """
    scope = 'login'


class RegistrationRateThrottle(AnonRateThrottle):
    """
    Without this, registration had no limit at all — enabling bulk
    fake-account creation, or (now that signup sends a real welcome
    email) using registration itself as a mail-spam vector against any
    target address willing to accept it.
    """
    scope = 'registration'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Without this, the password reset request endpoint could be used to
    mail-bomb an arbitrary email address with reset links, same as
    registration's own risk — and since this endpoint is unauthenticated
    by necessity, IP-based throttling is the only practical guard here.
    """
    scope = 'password_reset'