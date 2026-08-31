from django.conf import settings
from django.core.mail import send_mail


def _send(subject, message, to_email):
    """
    Deliberately duplicated from wallets/notifications.py's helper
    rather than imported — accounts is a more foundational app than
    wallets, so accounts importing from wallets would be a backwards
    dependency. A failed email must never break the actual password
    reset flow it's supporting.
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
        return False


def send_password_reset_email(user, reset_url):
    subject = "Reset your Clarastock password"
    message = (
        f"Hi {user.username},\n\n"
        f"We received a request to reset your Clarastock password. Click the link "
        f"below to choose a new one:\n\n"
        f"{reset_url}\n\n"
        f"This link expires soon and can only be used once. If you didn't request "
        f"this, you can safely ignore this email — your password hasn't been changed.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, user.email)


def send_password_changed_notification(user):
    subject = "Your Clarastock password was changed"
    message = (
        f"Hi {user.username},\n\n"
        f"Your password was just changed. If this wasn't you, please contact "
        f"support immediately.\n\n"
        f"— Clarastock"
    )
    return _send(subject, message, user.email)
