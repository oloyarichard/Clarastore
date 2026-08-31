from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import CartItem, Order, OrderItem
from catalog.serializers import ProductListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True, max_value=2147483647)
    size = serializers.CharField(required=False, allow_blank=True, max_length=20)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'size', 'subtotal', 'unit_price', 'negotiated_price', 'created_at']
        read_only_fields = ['id', 'product', 'subtotal', 'unit_price', 'negotiated_price', 'created_at']

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        if value > 1000:
            # Without an upper bound, an absurdly large integer passes
            # this validation fine and then crashes at the database
            # layer instead (confirmed directly: SQLite/Postgres both
            # overflow on a value this size, producing a raw 500
            # instead of a clean rejection). 1000 units in one cart
            # line is already far beyond any real customer's use case.
            raise serializers.ValidationError("Quantity is too large.")
        return value

    def validate_product_id(self, value):
        from catalog.models import Product
        try:
            product = Product.objects.get(pk=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
        if product.stock < 1:
            raise serializers.ValidationError("Product is out of stock.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'size', 'price_at_purchase', 'subtotal']


class OrderListSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    hub_name = serializers.CharField(source='hub.name', read_only=True)
    assigned_agent_name = serializers.CharField(source='assigned_agent.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'district_name', 'hub_name', 'assigned_agent_name',
            'status', 'total_amount', 'payment_status', 'created_at', 'items_count'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    hub_name = serializers.CharField(source='hub.name', read_only=True)
    assigned_agent_name = serializers.CharField(source='assigned_agent.username', read_only=True)
    customer_name = serializers.CharField(source='customer.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_name', 'district', 'district_name',
            'hub', 'hub_name', 'assigned_agent', 'assigned_agent_name',
            'status', 'transport_reference', 'total_amount', 'payment_status',
            'confirm_by', 'created_at', 'dispatched_at', 'delivered_at', 'items'
        ]


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status', 'transport_reference']

    def validate(self, data):
        order = self.instance
        user = self.context['request'].user
        new_status = data.get('status')

        if not new_status:
            return data

        # Define valid transitions per role
        valid_agent_transitions = {
            'assigned': ['picked_up'],
            'picked_up': ['dispatched', 'awaiting_confirmation'],
        }

        valid_customer_transitions = {
            'dispatched': ['delivered', 'flagged'],
            'picked_up': ['delivered', 'flagged'],
            'awaiting_confirmation': ['delivered', 'flagged'],
        }

        valid_admin_transitions = {
            'flagged': ['lost', 'delivered'],
            'pending': ['cancelled'],
            'assigned': ['cancelled'],
        }

        # Each relationship this user could have to the order is checked
        # independently, not as mutually-exclusive if/elif branches —
        # an agent buying for themselves is BOTH order.assigned_agent
        # AND order.customer on the same order, and needs access to
        # both transition tables depending on which action they're
        # taking (marking picked up vs. confirming they received it).
        # An if/elif here would let whichever check happens to be
        # listed first silently swallow the other, blocking a
        # legitimate transition the user genuinely has permission for.
        allowed = False

        if user.is_agent and order.assigned_agent == user:
            if new_status in valid_agent_transitions.get(order.status, []):
                allowed = True
            # For hub-direct orders, agent can go from picked_up to awaiting_confirmation
            # without dispatch step. For sub-districts, dispatched requires transport_reference.
            if order.status == 'picked_up' and new_status == 'dispatched':
                if order.district.type == 'sub':
                    if not data.get('transport_reference'):
                        raise serializers.ValidationError(
                            "Transport reference is required for sub-district dispatch."
                        )
                else:
                    raise serializers.ValidationError(
                        "Hub-direct orders cannot be dispatched. Use awaiting_confirmation."
                    )

        # Deliberately role-agnostic: whether this person's account is
        # labeled 'customer' or 'agent' doesn't matter here — what
        # matters is whether they're the actual recipient of THIS
        # order. An agent who bought something for themselves is still
        # the one who needs to confirm it arrived.
        if order.customer == user:
            if new_status in valid_customer_transitions.get(order.status, []):
                allowed = True

        if user.is_admin_role:
            if new_status in valid_admin_transitions.get(order.status, []):
                allowed = True

        if not allowed:
            raise serializers.ValidationError(
                f"Cannot transition from '{order.status}' to '{new_status}' with your role."
            )

        return data

    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        old_status = instance.status

        with transaction.atomic():
            if new_status == 'dispatched':
                instance.dispatched_at = timezone.now()
                instance.set_confirm_by()
            elif new_status == 'picked_up' and instance.district.type == 'hub':
                instance.set_confirm_by()
            elif new_status == 'delivered':
                instance.delivered_at = timezone.now()
                instance.confirm_by = None
                # Trigger commission calculation
                from wallets.services import calculate_commissions
                calculate_commissions(instance)
            elif new_status == 'lost':
                # process_refund now manages payment_status itself
                # (paid -> refund_processing -> refunded, or reverted
                # back to paid on failure) — setting it manually here
                # too would be redundant at best and confusing at
                # worst if this code is ever touched again later.
                from wallets.services import process_refund
                process_refund(instance)

            if new_status in ['flagged', 'lost']:
                instance.confirm_by = None

            instance = super().update(instance, validated_data)

            # Deferred to on_commit — a customer should never be told
            # "your order is on its way" for a status change that then
            # rolls back due to a later error in this same transaction.
            from wallets.notifications import (
                send_order_dispatched_notification,
                send_order_delivered_notification,
                send_order_flagged_notification,
            )
            if new_status == 'dispatched':
                transaction.on_commit(lambda: send_order_dispatched_notification(instance))
            elif new_status == 'delivered':
                transaction.on_commit(lambda: send_order_delivered_notification(instance))
            elif new_status == 'flagged':
                transaction.on_commit(lambda: send_order_flagged_notification(instance))

        return instance


class CheckoutSerializer(serializers.Serializer):
    district_id = serializers.IntegerField(max_value=2147483647)

    def validate_district_id(self, value):
        from accounts.models import District
        try:
            district = District.objects.get(pk=value)
        except District.DoesNotExist:
            raise serializers.ValidationError("District not found.")
        return value

    def validate(self, data):
        request = self.context['request']
        user = request.user

        # Get cart items
        cart_items = CartItem.objects.filter(user=user)
        if not cart_items.exists():
            raise serializers.ValidationError("Your cart is empty.")

        # Check stock
        for item in cart_items:
            if item.quantity > item.product.stock:
                raise serializers.ValidationError(
                    f"Insufficient stock for {item.product.name}. Available: {item.product.stock}"
                )

        # A negotiated price is only honorable for a limited window (see
        # NEGOTIATION_AGREEMENT_EXPIRY_HOURS) — if that's lapsed, block
        # checkout at the stale price rather than silently charging it or
        # silently reverting to the catalog price without telling anyone.
        for item in cart_items:
            if item.negotiation_id and not item.negotiation.is_agreement_still_valid:
                raise serializers.ValidationError(
                    f"Your negotiated price for {item.product.name} has expired. "
                    f"Please negotiate again or remove it from your cart."
                )

        # Calculate total
        total = sum(item.subtotal for item in cart_items)

        # Check wallet balance
        from wallets.models import Wallet
        try:
            wallet = Wallet.objects.select_for_update().get(user=user)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Wallet not found. Please contact support.")

        if wallet.balance < total:
            raise serializers.ValidationError(
                f"Insufficient wallet balance. Required: {total}, Available: {wallet.balance}"
            )

        data['cart_items'] = cart_items
        data['total'] = total
        data['wallet'] = wallet
        return data
