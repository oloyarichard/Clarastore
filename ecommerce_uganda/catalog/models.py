from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    seller_floor = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Absolute minimum acceptable price during negotiation. "
                   "Must be at least MINIMUM_MARGIN_PERCENT above cost_price. "
                   "Never shown to customers."
    )
    stock = models.PositiveIntegerField(default=0)
    # Fixed choices, not free text — each one maps to a specific sizing
    # behavior on the product page (see product_detail.html): clothes
    # get letter sizes, trousers and shoes get numeric sizes (waist and
    # UK shoe size respectively), accessories and other need no size
    # selector at all. Fully backward-compatible with existing usage —
    # filtering, search, and admin's list_filter all already work with
    # a plain CharField, and a fixed choices field only improves them
    # (an exact-match dropdown filter instead of arbitrary free text).
    CATEGORY_CHOICES = [
        ('clothes', 'Clothes'),
        ('trousers', 'Trousers'),
        ('shoes', 'Shoes'),
        ('accessories', 'Accessories'),
        ('other', 'Other'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_products',
        # No limit_choices_to here — this is purely informational tracking
        # of who created the product via Django admin. Django admin access
        # itself is already governed by is_staff/is_superuser, which is
        # unrelated to this app's own `role` field. Constraining this to
        # role='admin' looked reasonable but doesn't reflect reality (a
        # superuser account's role defaults to 'customer' unless someone
        # explicitly changes it) — combined with full_clean() running on
        # every save, that mismatch turns into a hard failure on every
        # product creation, not just a narrower dropdown.
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def minimum_allowed_floor(self):
        """
        The lowest seller_floor can legally be, given cost_price and the
        configured minimum margin. This is the actual safety boundary —
        everything else (admin UI, serializers, the negotiation engine)
        just surfaces or defers to this number.

        MINIMUM_MARGIN_PERCENT is stored as a fraction (0.10 = 10%),
        matching COMMISSION_RATE's existing convention in this project.
        """
        margin_fraction = Decimal(str(getattr(settings, 'MINIMUM_MARGIN_PERCENT', 0.10)))
        return (self.cost_price * (Decimal('1') + margin_fraction)).quantize(Decimal('0.01'))

    def clean(self):
        super().clean()
        if self.seller_floor is not None and self.seller_floor < self.minimum_allowed_floor:
            margin_percent_display = getattr(settings, 'MINIMUM_MARGIN_PERCENT', 0.10) * 100
            raise ValidationError({
                'seller_floor': (
                    f"Seller floor must be at least {self.minimum_allowed_floor} "
                    f"(cost price + {margin_percent_display:.0f}% minimum margin)."
                )
            })

    def save(self, *args, **kwargs):
        # full_clean() (not just clean()) so this fires on every save path,
        # including direct .save() calls that skip a serializer/form's own
        # validate() — this rule can't be silently bypassed.
        self.full_clean()
        super().save(*args, **kwargs)
