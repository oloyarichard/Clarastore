from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_items'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    # Free-text so it works for both clothing (S/M/L/XL) and shoe (UK
    # numeric) sizing without needing two separate fields — blank for
    # any product that doesn't need sizing at all.
    size = models.CharField(max_length=20, blank=True)
    # Set only when this item came from an agreed negotiation — locks the
    # price so checkout can never silently fall back to the live catalog
    # price. Left null for ordinary (non-negotiated) cart items.
    negotiated_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    negotiation = models.ForeignKey(
        'negotiations.NegotiationSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cart_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name='cart_item_has_owner'
            ),
            models.UniqueConstraint(
                fields=['user', 'product', 'size'],
                name='unique_user_cart_item',
                condition=models.Q(user__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['session_key', 'product', 'size'],
                name='unique_session_cart_item',
                condition=models.Q(session_key__isnull=False)
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        owner = self.user.username if self.user else self.session_key
        return f"{owner} - {self.product.name} x{self.quantity}"

    @property
    def unit_price(self):
        """The negotiated price if this item came from an agreement,
        otherwise the live catalog price."""
        return self.negotiated_price if self.negotiated_price is not None else self.product.price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('dispatched', 'Dispatched'),
        ('awaiting_confirmation', 'Awaiting Confirmation'),
        ('delivered', 'Delivered'),
        ('flagged', 'Flagged'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        # A transient guard state, not a real business status — set
        # briefly while a refund's external disbursement call is in
        # flight, so a second concurrent refund attempt for the same
        # order (a double-click, or two near-simultaneous status
        # transitions both triggering a refund) can be detected and
        # blocked before it ever reaches the payment gateway a second
        # time. Reverted back to 'paid' if the disbursement fails.
        ('refund_processing', 'Refund Processing'),
        ('refunded', 'Refunded'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    district = models.ForeignKey(
        'accounts.District',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    hub = models.ForeignKey(
        'accounts.District',
        on_delete=models.PROTECT,
        related_name='hub_orders',
        help_text="Resolved hub for delivery"
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
        limit_choices_to={'role': 'agent'}
    )
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    transport_reference = models.TextField(blank=True, help_text="Route/driver contact when dispatched")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(max_length=18, choices=PAYMENT_STATUS_CHOICES, default='paid')
    confirm_by = models.DateTimeField(null=True, blank=True, help_text="Delivery confirmation deadline")
    created_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.customer.username} - {self.status}"

    def resolve_hub(self):
        """Resolve the hub district for this order."""
        if self.district.type == 'hub':
            return self.district
        return self.district.forwarding_hub

    def set_confirm_by(self):
        """Set the confirmation deadline based on current status."""
        from django.conf import settings
        hours = getattr(settings, 'DELIVERY_CONFIRMATION_HOURS', 24)
        self.confirm_by = timezone.now() + timedelta(hours=hours)

    def save(self, *args, **kwargs):
        if self.district and not self.hub_id:
            self.hub = self.resolve_hub()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=20, blank=True)
    price_at_purchase = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.order.id} - {self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.price_at_purchase * self.quantity
