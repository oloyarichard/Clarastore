from rest_framework.throttling import SimpleRateThrottle


class NegotiationRateThrottle(SimpleRateThrottle):
    """
    Throttles negotiation start/offer requests by IP address —
    deliberately unconditional on login status, since guests can
    negotiate too, and a determined attacker could otherwise just clear
    cookies/sessions to sidestep any throttle keyed on something other
    than IP.

    This exists specifically because each negotiation request ties up
    the one shared, self-hosted Ollama instance for 10-90+ seconds —
    without this, a scripted burst of requests could keep it
    permanently busy, denying it to every real customer at once. A rate
    limit elsewhere in the app is about abuse in general; this one is
    about protecting a specific, genuinely scarce shared resource.
    """
    scope = 'negotiation'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
