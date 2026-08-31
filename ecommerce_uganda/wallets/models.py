from django.db import models
from django.conf import settings


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Wallet for {self.user.username}: {self.balance}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('topup_gateway', 'Top-up via Gateway'),
        ('topup_via_agent_credit', 'Top-up via Agent (Credit)'),
        ('topup_via_agent_debit', 'Top-up via Agent (Debit)'),
        ('payment', 'Payment'),
        ('commission', 'Commission'),
        ('commission_reversal', 'Commission Reversal (Refund Clawback)'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=255, blank=True, help_text="Order ID, paired transaction UUID, etc.")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_transactions'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} | {self.amount} | {self.wallet.user.username}"

    def delete(self, *args, **kwargs):
        raise models.ProtectedError("WalletTransaction records are immutable and cannot be deleted.", self)


class TopUpRequest(models.Model):
    """
    Tracks an in-flight mobile money top-up request (MTN MoMo or Airtel
    Money). Both providers are asynchronous: we initiate a request, the
    customer approves on their phone, and we confirm afterwards via
    polling or a callback. The wallet is only credited once status
    becomes 'successful' — see wallets.services.confirm_gateway_topup.
    """
    PROVIDER_CHOICES = [
        ('gosentepay', 'GosentePay'),
        ('mtn_momo', 'MTN MoMo'),
        ('airtel_money', 'Airtel Money'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='topup_requests'
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    external_reference = models.CharField(
        max_length=255, unique=True,
        help_text="Provider-side reference (MTN referenceId / Airtel transaction id)"
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    wallet_transaction = models.OneToOneField(
        WalletTransaction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='topup_request'
    )
    raw_response = models.JSONField(default=dict, blank=True, help_text="Last raw status payload from provider")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.provider} {self.amount} - {self.user.username} ({self.status})"


class AgentCommission(models.Model):
    order_item = models.OneToOneField(
        'orders.OrderItem',
        on_delete=models.PROTECT,
        related_name='commission'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='commissions',
        limit_choices_to={'role': 'agent'}
    )
    profit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    wallet_transaction = models.OneToOneField(
        WalletTransaction,
        on_delete=models.PROTECT,
        related_name='commission'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commission {self.commission_amount} for {self.agent.username} on OrderItem {self.order_item.id}"


class RefundDisbursement(models.Model):
    """
    A real money movement out of the business's own GoSentePay balance,
    directly to a customer's mobile money account — unlike the old
    refund behavior, this never touches the customer's internal
    wallet at all. This is the concrete record of "our revenue gets
    debited" for a refund: real money the business actually paid out,
    not just an internal ledger credit.
    """
    STATUS_CHOICES = [
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        # Set only if a later callback ever contradicts a disbursement
        # already recorded as successful — genuinely rare, and never
        # resolved automatically (see RefundCallbackView): reversing an
        # already-completed refund (un-refunding an order, reversing a
        # commission clawback reversal) is a business decision, not
        # something safe to silently automate.
        ('disputed', 'Disputed — needs admin review'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='refund_disbursement'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    external_reference = models.CharField(max_length=100)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='successful')
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='refunds_issued',
        help_text="The admin who issued this refund, if triggered manually rather than automatically."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.amount} for Order #{self.order_id} ({self.status})"
