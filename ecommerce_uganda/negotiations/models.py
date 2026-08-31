from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class MarketSnapshot(models.Model):
    """
    A normalized, timestamped read of a product's market signals. The
    negotiation engine always negotiates against the latest non-expired
    snapshot rather than recalculating live on every offer — keeps AI
    calls fast and signal calculation cheap (per the spec's cache/cost
    control requirement).
    """
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='market_snapshots')

    # Internal signals (highest priority per the agreed weighting)
    sales_velocity = models.FloatField(default=0, help_text="Units sold per day, recent window")
    demand_score = models.FloatField(default=0, help_text="0-1, derived from views/cart-adds/sales")
    inventory_pressure = models.FloatField(default=0, help_text="0-1, higher = lower stock relative to demand")

    # External signal (second priority) — currently a manual/config value,
    # not yet wired to a live exchange-rate API (see negotiations/services.py)
    exchange_rate_signal = models.FloatField(default=0, help_text="-1 to 1, UGX/USD movement adjustment")

    # Seasonal signal (third priority, bounded)
    seasonal_signal = models.FloatField(default=0, help_text="-1 to 1, bounded seasonal demand adjustment")

    calculated_market_price = models.DecimalField(max_digits=12, decimal_places=2)
    confidence = models.FloatField(default=0, help_text="0-1 — how much real data backs this snapshot")

    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"Snapshot for {self.product.name} @ {self.generated_at:%Y-%m-%d %H:%M}"

    @property
    def is_fresh(self):
        return timezone.now() < self.expires_at


class NegotiationSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('agreed', 'Agreed'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('abandoned', 'Abandoned'),
    ]

    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='negotiations')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='negotiations'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='active')
    market_snapshot = models.ForeignKey(
        MarketSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name='negotiations'
    )

    agreed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    agreed_at = models.DateTimeField(null=True, blank=True)
    # Per the 24-hour rule: an agreed price stops being honorable at checkout
    # after this point.
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name='negotiation_has_owner'
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        owner = self.user.username if self.user else self.session_key
        return f"Negotiation #{self.id} - {owner} - {self.product.name} ({self.status})"

    def mark_agreed(self, price):
        self.status = 'agreed'
        self.agreed_price = price
        self.agreed_at = timezone.now()
        hours = getattr(settings, 'NEGOTIATION_AGREEMENT_EXPIRY_HOURS', 24)
        self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
        self.save(update_fields=['status', 'agreed_price', 'agreed_at', 'expires_at', 'updated_at'])

    @property
    def is_agreement_still_valid(self):
        return (
            self.status == 'agreed'
            and self.expires_at is not None
            and timezone.now() < self.expires_at
        )


class NegotiationOffer(models.Model):
    """
    One row per turn — either the customer's offer or the AI's response.
    This is the full audit trail the spec requires: every decision must
    be traceable back to the exact offer, snapshot, and raw AI output
    that produced it.
    """
    TURN_TYPE_CHOICES = [
        ('customer_offer', 'Customer Offer'),
        ('ai_response', 'AI Response'),
    ]
    DECISION_CHOICES = [
        ('ACCEPT', 'Accept'),
        ('COUNTER', 'Counter'),
        ('REJECT', 'Reject'),
    ]

    negotiation = models.ForeignKey(NegotiationSession, on_delete=models.CASCADE, related_name='offers')
    turn_type = models.CharField(max_length=15, choices=TURN_TYPE_CHOICES)

    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES, blank=True)
    message = models.TextField(blank=True)

    # Full traceability per the spec's auditability requirement
    market_snapshot = models.ForeignKey(
        MarketSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name='offers'
    )
    raw_ai_output = models.JSONField(default=dict, blank=True)
    # What the AI actually proposed, vs. what the backend allowed through —
    # these can differ if the backend had to override/clamp the AI's price.
    ai_proposed_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    was_backend_overridden = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.negotiation_id} - {self.turn_type} - {self.amount}"
