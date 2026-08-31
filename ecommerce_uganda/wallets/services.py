import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .gateways import GatewayError, get_gateway
from .models import AgentCommission, RefundDisbursement, TopUpRequest, Wallet, WalletTransaction
from .notifications import (
    send_commission_clawback_notification,
    send_commission_earned_notification,
    send_refund_notification,
)

logger = logging.getLogger(__name__)


def calculate_commissions(order):
    """
    Called when an order transitions to 'delivered'. Credits the assigned
    agent 10% of profit on every item in the order. Idempotent: items that
    already have a linked AgentCommission are skipped, so calling this twice
    for the same order never double-pays.
    """
    agent = order.assigned_agent
    if not agent:
        return

    rate = Decimal(str(settings.COMMISSION_RATE))
    total_credited = Decimal('0')

    with transaction.atomic():
        wallet, _ = Wallet.objects.get_or_create(user=agent)
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        for item in order.items.select_related('product').all():
            if hasattr(item, 'commission'):
                continue  # already paid out

            profit_per_unit = item.price_at_purchase - item.product.cost_price
            profit_amount = (profit_per_unit * item.quantity).quantize(Decimal('0.01'))
            commission_amount = (profit_amount * rate).quantize(Decimal('0.01'))

            wallet.balance += commission_amount
            wallet.save(update_fields=['balance'])

            wallet_txn = WalletTransaction.objects.create(
                wallet=wallet,
                type='commission',
                amount=commission_amount,
                balance_after=wallet.balance,
                reference=f"ORDER_{order.id}_ITEM_{item.id}",
            )
            AgentCommission.objects.create(
                order_item=item,
                agent=agent,
                profit_amount=profit_amount,
                commission_amount=commission_amount,
                wallet_transaction=wallet_txn,
            )
            total_credited += commission_amount

        if total_credited > 0:
            # One email per order, not per item — and only if this call
            # actually credited something new (a repeat, idempotent
            # call on an already-paid order sends nothing).
            transaction.on_commit(lambda: send_commission_earned_notification(agent, order, total_credited))


def process_refund(order, initiated_by=None):
    """
    Refunds the full order total directly to the customer's real mobile
    money account via GoSentePay — money genuinely leaves the business,
    unlike the old behavior of just crediting the customer's internal
    wallet. Also reverses any agent commission that was already paid
    on this order (it had reached 'delivered' before being refunded);
    if commission was never paid (the order never reached 'delivered'
    — e.g. a 'lost' order), there's nothing to claw back, since
    calculate_commissions never ran for it in the first place.

    Raises ValidationError if the order was already refunded (or a
    refund is already in flight for it), or if the disbursement
    itself fails — in the failure case, nothing is changed: no
    commission is reversed, no status is left altered, exactly as if
    the refund was never attempted.

    Guards against a genuine race condition: two near-simultaneous
    calls for the same order (an admin double-click, or two status
    transitions both triggering a refund) could otherwise both pass
    a same-status check before either updates it, both reach the
    external payment call, and both actually disburse money —
    GoSentePay's own duplicate-reference protection wouldn't catch
    this either, since each call generates a different reference. A
    short-lived transaction claims the order with a transient
    'refund_processing' state before the slow external call is ever
    made, and is reverted if that call fails, so a genuine retry
    remains possible.
    """
    with transaction.atomic():
        from orders.models import Order
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.payment_status != 'paid':
            raise ValidationError(
                f"This order cannot be refunded right now (payment status: {locked_order.payment_status})."
            )
        locked_order.payment_status = 'refund_processing'
        locked_order.save(update_fields=['payment_status'])
    # Lock released here, before the slow network call — any concurrent
    # attempt from this point on sees 'refund_processing', not 'paid',
    # and is blocked by the check above.

    customer = order.customer
    if not customer.phone:
        Order.objects.filter(pk=order.pk).update(payment_status='paid')
        raise ValidationError("Customer has no phone number on file — cannot disburse a refund.")

    gateway = get_gateway('gosentepay')
    external_id = str(uuid.uuid4())

    try:
        gateway.disburse(
            customer.phone, order.total_amount, customer.email,
            reason=f"Refund for Order #{order.id}", external_id=external_id,
        )
    except GatewayError as e:
        # Revert the guard state so a genuine retry is possible —
        # nothing was actually disbursed.
        Order.objects.filter(pk=order.pk).update(payment_status='paid')
        raise ValidationError(f"Refund disbursement failed: {e}")

    clawed_back_agent = None
    clawed_back_amount = Decimal('0')

    with transaction.atomic():
        order.refresh_from_db()
        RefundDisbursement.objects.create(
            order=order, amount=order.total_amount,
            external_reference=external_id, status='successful',
            initiated_by=initiated_by,
        )
        order.payment_status = 'refunded'
        order.save(update_fields=['payment_status'])

        # Claw back commission only for items where it was actually
        # paid — calculate_commissions only ever runs on the
        # 'delivered' transition, so an order that never reached that
        # status (e.g. 'lost') simply has nothing here to reverse.
        for item in order.items.select_related('commission', 'commission__agent'):
            if not hasattr(item, 'commission'):
                continue
            commission = item.commission
            agent_wallet = Wallet.objects.select_for_update().get(user=commission.agent)
            agent_wallet.balance -= commission.commission_amount
            agent_wallet.save(update_fields=['balance'])
            WalletTransaction.objects.create(
                wallet=agent_wallet,
                type='commission_reversal',
                amount=-commission.commission_amount,
                balance_after=agent_wallet.balance,
                reference=f"ORDER_{order.id}_REFUND_CLAWBACK",
            )
            clawed_back_agent = commission.agent
            clawed_back_amount += commission.commission_amount

    # Emails happen after the transaction commits — a failed email
    # must never look like it rolled back money that already moved.
    send_refund_notification(order, order.total_amount)
    if clawed_back_agent:
        send_commission_clawback_notification(clawed_back_agent, order, clawed_back_amount)

    return order


def agent_topup_customer(agent, customer, amount):
    """
    Move `amount` from the agent's own wallet to a customer's wallet
    (agent collected cash in person and is crediting the customer's
    account). Blocked if it would drop the agent below the required
    standing minimum float (AGENT_MINIMUM_FLOAT) — the agent must always
    keep at least that much available, not just reach it once.
    """
    if amount <= 0:
        raise ValidationError("Amount must be positive.")

    min_float = Decimal(str(settings.AGENT_MINIMUM_FLOAT))
    reference = str(uuid.uuid4())

    with transaction.atomic():
        agent_wallet = Wallet.objects.select_for_update().get(user=agent)
        customer_wallet = Wallet.objects.select_for_update().get(user=customer)

        if agent_wallet.balance - amount < min_float:
            raise ValidationError(
                f"This would drop your float below the required minimum of "
                f"{min_float}. Top up your own wallet first."
            )

        agent_wallet.balance -= amount
        agent_wallet.save(update_fields=['balance'])
        WalletTransaction.objects.create(
            wallet=agent_wallet,
            type='topup_via_agent_debit',
            amount=-amount,
            balance_after=agent_wallet.balance,
            reference=reference,
            created_by=agent,
        )

        customer_wallet.balance += amount
        customer_wallet.save(update_fields=['balance'])
        WalletTransaction.objects.create(
            wallet=customer_wallet,
            type='topup_via_agent_credit',
            amount=amount,
            balance_after=customer_wallet.balance,
            reference=reference,
            created_by=agent,
        )

    return reference


def initiate_gateway_topup(user, amount, phone_number, provider):
    """
    Starts a mobile money top-up: asks MTN MoMo or Airtel Money to push a
    payment request to the customer's phone. Nothing is credited yet — the
    customer still has to approve the PIN prompt on their device. Returns
    the TopUpRequest record the client should poll (or wait on a callback
    for) to find out the outcome.
    """
    if amount <= 0:
        raise ValidationError("Amount must be positive.")
    if provider not in dict(TopUpRequest.PROVIDER_CHOICES):
        raise ValidationError(f"Unknown provider: {provider}")

    external_id = str(uuid.uuid4())
    gateway = get_gateway(provider)

    try:
        reference_id = gateway.request_payment(phone_number, amount, external_id, email=user.email)
    except GatewayError as e:
        # The real, technical cause (a raw gateway status code, a DNS
        # failure, whatever it actually was) gets logged for whoever's
        # debugging this later — a customer trying to top up their
        # wallet should never see something like "GosentePay deposit
        # request failed: 400 {'status': 'invalidPhone'}" or a raw
        # connection error message.
        logger.warning(f"Gateway top-up failed for user {user.id}: {e}")
        raise ValidationError(
            "We couldn't start that top-up right now — please double-check your phone "
            "number and try again, or contact support if this keeps happening."
        )

    return TopUpRequest.objects.create(
        user=user,
        provider=provider,
        phone_number=phone_number,
        amount=amount,
        external_reference=reference_id,
        status='pending',
    )


def confirm_gateway_topup(topup_request):
    """
    Checks the current status of a pending TopUpRequest with the provider
    and, on success, credits the wallet exactly once. Safe to call
    repeatedly while polling — once a request is no longer 'pending' this
    is a no-op. Returns the (possibly updated) TopUpRequest.
    """
    if topup_request.status != 'pending':
        return topup_request

    gateway = get_gateway(topup_request.provider)
    try:
        provider_status = gateway.check_status(topup_request.external_reference)
    except GatewayError as e:
        logger.warning(f"Gateway status check failed for TopUpRequest {topup_request.id}: {e}")
        raise ValidationError(
            "We couldn't check on that top-up right now — please try again in a moment."
        )

    if provider_status == 'pending':
        return topup_request

    with transaction.atomic():
        # Re-fetch and lock so two concurrent status checks can't both credit.
        topup_request = TopUpRequest.objects.select_for_update().get(pk=topup_request.pk)
        if topup_request.status != 'pending':
            return topup_request

        if provider_status == 'successful':
            wallet, _ = Wallet.objects.get_or_create(user=topup_request.user)
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            wallet.balance += topup_request.amount
            wallet.save(update_fields=['balance'])

            wallet_txn = WalletTransaction.objects.create(
                wallet=wallet,
                type='topup_gateway',
                amount=topup_request.amount,
                balance_after=wallet.balance,
                reference=f"{topup_request.provider}:{topup_request.external_reference}",
            )
            topup_request.status = 'successful'
            topup_request.wallet_transaction = wallet_txn
        else:
            topup_request.status = 'failed'

        topup_request.save(update_fields=['status', 'wallet_transaction', 'updated_at'])

    return topup_request
