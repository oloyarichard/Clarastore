from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import CartItem, Order, OrderItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'product', 'quantity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name', 'session_key']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']

    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'district', 'hub', 'assigned_agent',
        'status', 'total_amount', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'district', 'hub', 'created_at']
    search_fields = ['customer__username', 'id', 'transport_reference']
    readonly_fields = ['created_at', 'dispatched_at', 'delivered_at']
    inlines = [OrderItemInline]
    actions = ['refund_orders']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'district', 'hub', 'assigned_agent'
        )

    def changelist_view(self, request, extra_context=None):
        # Add a quick link to flagged orders
        extra_context = extra_context or {}
        extra_context['flagged_count'] = Order.objects.filter(status='flagged').count()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="Refund selected orders (disbursed via GoSentePay)")
    def refund_orders(self, request, queryset):
        """
        Sends the full order total directly to the customer's real
        mobile money account — actual money leaving the business, not
        an internal wallet credit. Any commission already paid to the
        assigned agent on a refunded order is automatically clawed
        back; commission never paid (the order never reached
        'delivered') is simply never paid, nothing to reverse.
        """
        from wallets.services import process_refund

        succeeded, failed = 0, []
        for order in queryset:
            try:
                process_refund(order, initiated_by=request.user)
                succeeded += 1
            except ValidationError as e:
                failed.append(f"Order #{order.id}: {e}")

        if succeeded:
            self.message_user(request, f"Refunded {succeeded} order(s) via GoSentePay.", level=messages.SUCCESS)
        for msg in failed:
            self.message_user(request, msg, level=messages.ERROR)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price_at_purchase', 'subtotal']
    list_filter = ['order__status']
    search_fields = ['order__id', 'product__name']

    def subtotal(self, obj):
        return obj.subtotal

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'product')
