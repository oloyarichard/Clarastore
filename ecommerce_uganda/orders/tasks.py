from celery import shared_task
from django.utils import timezone
from .models import Order


@shared_task
def auto_flag_overdue_orders():
    """
    Check for orders past their confirm_by deadline that are still not delivered.
    Auto-flag them for investigation.
    """
    now = timezone.now()
    overdue_orders = Order.objects.filter(
        confirm_by__lt=now,
        status__in=['dispatched', 'awaiting_confirmation']
    )

    count = 0
    for order in overdue_orders:
        order.status = 'flagged'
        order.confirm_by = None
        order.save(update_fields=['status', 'confirm_by'])
        count += 1

    return f"Auto-flagged {count} overdue orders."
