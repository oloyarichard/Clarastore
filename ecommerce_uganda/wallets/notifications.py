from django.conf import settings
from django.core.mail import send_mail


def _send(subject, message, to_email):
    """
    Thin wrapper around Django's send_mail — kept in one place so every
    notification goes through the same error handling. A failed email
    (bad SMTP config, network issue) must never break the actual
    financial transaction it's reporting on; callers should call this
    after the money has already moved, not as a precondition for it.
    """
    if not to_email:
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
        return True
    except Exception:
        # fail_silently=True already covers most SMTP-level errors, but
        # this is a deliberate last-resort net — a notification email
        # should never be the reason a refund appears to have crashed.
        return False


def send_refund_notification(order, amount):
    subject = f"Your refund for Order #{order.id} has been processed"
    message = (
        f"Hi {order.customer.username},\n\n"
        f"A refund of UGX {amount} for Order #{order.id} has been sent to your "
        f"mobile money account ({order.customer.phone}).\n\n"
        f"If you don't see it within a few minutes, please contact support.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, order.customer.email)


def send_commission_clawback_notification(agent, order, amount):
    subject = f"Commission reversed for Order #{order.id}"
    message = (
        f"Hi {agent.username},\n\n"
        f"Order #{order.id} has been refunded to the customer. Since your "
        f"commission of UGX {amount} on this order was already paid out, "
        f"it has been deducted from your wallet balance.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, agent.email)


def send_welcome_notification(user):
    subject = "Welcome to Clarastock"
    message = (
        f"Hi {user.username},\n\n"
        f"Your Clarastock account is ready. Browse the shop, negotiate a "
        f"price on anything that catches your eye, and we'll deliver it "
        f"to your district.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, user.email)


def send_order_placed_notification(order):
    subject = f"Order #{order.id} confirmed"
    message = (
        f"Hi {order.customer.username},\n\n"
        f"Your order #{order.id} for UGX {order.total_amount} has been "
        f"placed and is being prepared for delivery to {order.district.name}.\n\n"
        f"We'll email you again once it's on its way.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, order.customer.email)


def send_order_dispatched_notification(order):
    subject = f"Order #{order.id} is on its way"
    message = (
        f"Hi {order.customer.username},\n\n"
        f"Your order #{order.id} has been dispatched"
        + (f" (transport reference: {order.transport_reference})" if order.transport_reference else "")
        + f" and is on its way to you.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, order.customer.email)


def send_order_delivered_notification(order):
    subject = f"Order #{order.id} delivered"
    message = (
        f"Hi {order.customer.username},\n\n"
        f"Your order #{order.id} has been marked as delivered. We hope you "
        f"love it! If anything's wrong, let us know from your order page.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, order.customer.email)


def send_order_flagged_notification(order):
    subject = f"There's an issue with Order #{order.id}"
    message = (
        f"Hi {order.customer.username},\n\n"
        f"Your order #{order.id} has been flagged for review — this "
        f"usually means delivery couldn't be confirmed as expected. Our "
        f"team is looking into it, and we'll follow up shortly.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, order.customer.email)


def send_commission_earned_notification(agent, order, amount):
    subject = f"You earned a commission on Order #{order.id}"
    message = (
        f"Hi {agent.username},\n\n"
        f"You've earned UGX {amount} in commission on Order #{order.id}, "
        f"now credited to your wallet.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, agent.email)


def send_wallet_adjustment_notification(user, old_balance, new_balance):
    subject = "Your Clarastock wallet balance has been updated"
    difference = new_balance - old_balance
    direction = "credited" if difference >= 0 else "debited"
    message = (
        f"Hi {user.username},\n\n"
        f"Your wallet has been {direction} UGX {abs(difference)} by our team. "
        f"Your new balance is UGX {new_balance}.\n\n"
        f"If you weren't expecting this, please contact support.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, user.email)


def send_refund_disputed_alert(refund_disbursement, provider_reported_status):
    """
    Sent to every admin/superuser, not the customer — this represents a
    genuine discrepancy that needs a human decision, not something to
    resolve silently. See RefundDisbursement.STATUS_CHOICES for why
    this is never auto-reversed.
    """
    from django.conf import settings as django_settings
    from accounts.models import User

    subject = f"ACTION NEEDED: refund for Order #{refund_disbursement.order_id} is disputed"
    message = (
        f"A refund we recorded as successful is now being reported "
        f"differently by GoSentePay.\n\n"
        f"Order: #{refund_disbursement.order_id}\n"
        f"Amount: UGX {refund_disbursement.amount}\n"
        f"Reference: {refund_disbursement.external_reference}\n"
        f"Originally recorded as: successful\n"
        f"GoSentePay now reports: {provider_reported_status}\n\n"
        f"This was NOT reversed automatically — please review manually in "
        f"Django admin under Wallets > Refund disbursements before taking "
        f"any action (the customer may or may not have actually received "
        f"the money; the order and any commission clawback were left as-is)."
    )
    admin_emails = list(
        User.objects.filter(is_superuser=True).exclude(email='').values_list('email', flat=True)
    )
    sent = False
    for email in admin_emails:
        if _send(subject, message, email):
            sent = True
    return sent
