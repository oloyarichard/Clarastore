from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import NegotiationSession


@shared_task
def expire_stale_agreements():
    """
    An agreed negotiated price is only honorable for
    NEGOTIATION_AGREEMENT_EXPIRY_HOURS. Anything agreed longer ago than
    that, still sitting uncompleted, gets marked expired — and the cart
    item holding that locked price is released back to the live catalog
    price (or removed, if nothing else justifies it still being there).
    """
    now = timezone.now()
    stale = NegotiationSession.objects.filter(status='agreed', expires_at__lt=now)

    count = 0
    for negotiation in stale:
        negotiation.status = 'expired'
        negotiation.save(update_fields=['status', 'updated_at'])

        # Release any cart item still holding this negotiation's locked
        # price — checkout must never use an expired agreed price.
        for cart_item in negotiation.cart_items.all():
            cart_item.negotiated_price = None
            cart_item.negotiation = None
            cart_item.save(update_fields=['negotiated_price', 'negotiation', 'updated_at'])
        count += 1

    return f"Expired {count} stale negotiation agreements."


@shared_task
def expire_inactive_carts():
    """
    Any cart item — negotiated or not — that hasn't been touched in
    CART_INACTIVITY_EXPIRY_HOURS gets cleared. This is a new rule for the
    existing cart system, not specific to negotiation, but lives here
    since it was introduced alongside the negotiation layer's own 24-hour
    rule and shares the same Celery beat schedule.
    """
    from orders.models import CartItem

    hours = getattr(settings, 'CART_INACTIVITY_EXPIRY_HOURS', 24)
    cutoff = timezone.now() - timezone.timedelta(hours=hours)

    stale_items = CartItem.objects.filter(updated_at__lt=cutoff)
    count = stale_items.count()
    stale_items.delete()

    return f"Cleared {count} inactive cart items."


@shared_task
def refresh_market_snapshots():
    """
    Periodic background recalculation of market signals for products
    that have an active negotiation right now — this is the boundary the
    spec asks for between real-time negotiation calls (which must stay
    fast and cheap) and background market analysis (which can take its
    time). Negotiation itself never triggers a recalculation directly;
    it just reads whatever snapshot this task last produced.
    """
    from catalog.models import Product
    from .services import calculate_market_snapshot

    product_ids = NegotiationSession.objects.filter(
        status='active'
    ).values_list('product_id', flat=True).distinct()

    count = 0
    for product in Product.objects.filter(id__in=product_ids):
        calculate_market_snapshot(product)
        count += 1

    return f"Refreshed market snapshots for {count} products with active negotiations."
