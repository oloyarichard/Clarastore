from django import template
from django.db.models import Sum

register = template.Library()


@register.inclusion_tag('admin/_dashboard_stats.html')
def dashboard_stats():
    """
    Real business metrics for the admin homepage — order counts by
    status, agents below their required float minimum, product/user
    totals — replacing Django's default "list of app links" index page.
    """
    from accounts.models import User
    from catalog.models import Product
    from orders.models import Order
    from wallets.models import Wallet

    orders_qs = Order.objects.all()
    flagged_count = orders_qs.filter(status='flagged').count()
    active_count = orders_qs.filter(status__in=['pending', 'assigned', 'picked_up', 'dispatched']).count()
    delivered_count = orders_qs.filter(status='delivered').count()

    total_revenue = orders_qs.filter(payment_status='paid').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    low_float_agents = 0
    for wallet in Wallet.objects.select_related('user').filter(user__role='agent'):
        if wallet.balance < 100000:
            low_float_agents += 1

    return {
        'stats': [
            {'label': 'Flagged orders', 'value': flagged_count, 'alert': flagged_count > 0},
            {'label': 'Active orders', 'value': active_count, 'accent': False},
            {'label': 'Delivered orders', 'value': delivered_count, 'accent': False},
            {'label': 'Total revenue', 'value': f'UGX {total_revenue:,.0f}', 'accent': True},
            {'label': 'Products', 'value': Product.objects.count(), 'accent': False},
            {'label': 'Customers', 'value': User.objects.filter(role='customer').count(), 'accent': False},
            {'label': 'Agents', 'value': User.objects.filter(role='agent').count(), 'accent': False},
            {'label': 'Agents below float minimum', 'value': low_float_agents, 'alert': low_float_agents > 0},
        ]
    }
