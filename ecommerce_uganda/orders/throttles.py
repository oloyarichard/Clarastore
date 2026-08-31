from rest_framework.throttling import UserRateThrottle


class CheckoutRateThrottle(UserRateThrottle):
    """
    Checkout had no throttle at all — a customer with enough wallet
    balance could otherwise fire off checkouts as fast as their
    connection allowed, each one a real database write and (now) a
    real confirmation email. UserRateThrottle falls back to IP-based
    identification for any request that somehow reaches this
    unauthenticated, which shouldn't normally happen here since
    checkout requires a logged-in wallet owner anyway.
    """
    scope = 'checkout'


class OrderStatusRateThrottle(UserRateThrottle):
    """
    Status transitions can trigger real external side effects —
    commission crediting, and a 'lost' transition triggers an actual
    GoSentePay refund disbursement. Hammering this endpoint repeatedly
    was previously unthrottled, risking wasted load and unnecessary
    calls to a real payment API (the refund race-condition guard
    already prevents a double-disbursement specifically, but nothing
    previously stopped a flood of legitimate-looking transition
    attempts from being made in the first place).
    """
    scope = 'order_status'


class CartRateThrottle(UserRateThrottle):
    """
    Adding to cart had no limit — low severity on its own, but cheap
    to close and prevents using it to bloat storage with rapid,
    repeated additions.
    """
    scope = 'cart'
