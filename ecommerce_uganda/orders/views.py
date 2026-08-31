from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q

from .models import CartItem, Order, OrderItem
from .serializers import (
    CartItemSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderStatusUpdateSerializer,
    CheckoutSerializer,
)
from accounts.permissions import IsAdmin, IsAgent, IsOrderOwnerOrAgent
from .throttles import CartRateThrottle, CheckoutRateThrottle, OrderStatusRateThrottle


# --- Cart Views ---

class CartView(APIView):
    throttle_classes = [CartRateThrottle]

    def get_permissions(self):
        return [AllowAny()]

    def get_session_key(self, request):
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key

    def get_cart_items(self, request):
        if request.user.is_authenticated:
            return CartItem.objects.filter(user=request.user)
        session_key = self.get_session_key(request)
        return CartItem.objects.filter(session_key=session_key)

    def get(self, request):
        items = self.get_cart_items(request)
        serializer = CartItemSerializer(items, many=True)
        total = sum(item.subtotal for item in items)
        return Response({
            'items': serializer.data,
            'total': total,
            'count': items.count()
        })

    def post(self, request):
        """Add item to cart."""
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        size = serializer.validated_data.get('size', '')

        from catalog.models import Product
        product = Product.objects.get(pk=product_id)

        if request.user.is_authenticated:
            # size is part of the lookup, not just defaults — different
            # sizes of the same product are separate cart lines, never
            # silently merged into one with an ambiguous size.
            item, created = CartItem.objects.get_or_create(
                user=request.user,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )
            if not created:
                item.quantity += quantity
                item.save()
        else:
            session_key = self.get_session_key(request)
            item, created = CartItem.objects.get_or_create(
                session_key=session_key,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )
            if not created:
                item.quantity += quantity
                item.save()

        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        """Update cart item quantity."""
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        if not item_id or quantity is None:
            return Response(
                {"error": "item_id and quantity are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        items = self.get_cart_items(request)
        try:
            item = items.get(pk=item_id)
        except CartItem.DoesNotExist:
            return Response({"error": "Item not found in cart."}, status=status.HTTP_404_NOT_FOUND)

        if quantity < 1:
            item.delete()
            return Response({"message": "Item removed from cart."})

        if quantity > item.product.stock:
            return Response(
                {"error": f"Insufficient stock. Available: {item.product.stock}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        item.quantity = quantity
        item.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request):
        """Clear cart or remove specific item."""
        item_id = request.data.get('item_id')
        items = self.get_cart_items(request)

        if item_id:
            items.filter(pk=item_id).delete()
            return Response({"message": "Item removed from cart."})
        else:
            items.delete()
            return Response({"message": "Cart cleared."})


class MergeCartView(APIView):
    """
    Merge guest cart into user cart on login/signup. Reads the session key
    from the current request's session cookie automatically — the browser
    sends that cookie on this request regardless of which auth scheme
    matched the user (JWT here), so an explicit session_key in the body
    isn't needed. Session cookies are HttpOnly by default, so JS on a
    plain website couldn't read and forward the value anyway; an explicit
    session_key is still accepted as a fallback for clients that manage
    their own cookie jar (e.g. a native app) and already have it on hand.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_key = request.session.session_key or request.data.get('session_key')
        if not session_key:
            return Response({"message": "No guest session to merge."})

        guest_items = CartItem.objects.filter(session_key=session_key)

        with transaction.atomic():
            for guest_item in guest_items:
                # size is part of the lookup here too, for the same
                # reason as CartView.post — merging a guest's size-M
                # and size-L picks of the same product must never
                # collapse into one ambiguous line.
                user_item, created = CartItem.objects.get_or_create(
                    user=request.user,
                    product=guest_item.product,
                    size=guest_item.size,
                    defaults={'quantity': guest_item.quantity}
                )
                if not created:
                    user_item.quantity += guest_item.quantity
                    # Cap at available stock
                    if user_item.quantity > guest_item.product.stock:
                        user_item.quantity = guest_item.product.stock
                    user_item.save()

            guest_items.delete()

        return Response({"message": "Cart merged successfully."})


# --- Order Views ---

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CheckoutRateThrottle]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        cart_items = serializer.validated_data['cart_items']
        total = serializer.validated_data['total']
        wallet = serializer.validated_data['wallet']
        district_id = serializer.validated_data['district_id']

        from accounts.models import District
        district = District.objects.get(pk=district_id)
        hub = district.forwarding_hub if district.type == 'sub' else district

        # Deduct from wallet
        from wallets.models import WalletTransaction
        wallet.balance -= total
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            type='payment',
            amount=-total,
            balance_after=wallet.balance,
            reference=f"ORDER_PENDING"
        )

        # Create order
        order = Order.objects.create(
            customer=user,
            district=district,
            hub=hub,
            total_amount=total,
            status='pending',
            payment_status='paid'
        )

        # Create order items and decrement stock
        order_items = []
        for cart_item in cart_items:
            order_items.append(OrderItem(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                size=cart_item.size,
                price_at_purchase=cart_item.unit_price
            ))
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()

        OrderItem.objects.bulk_create(order_items)

        # Clear cart
        cart_items.delete()

        # Auto-assign agent
        assigned = self.assign_agent(order)
        if assigned:
            order.status = 'assigned'
            order.save()
            # Update payment transaction reference
            WalletTransaction.objects.filter(
                wallet=wallet,
                type='payment',
                reference='ORDER_PENDING'
            ).update(reference=f"ORDER_{order.id}")

        # Deferred until the transaction actually commits — this whole
        # view runs inside @transaction.atomic, so sending the email
        # any earlier risks confirming an order that could still roll
        # back due to a later error in this same request.
        from wallets.notifications import send_order_placed_notification
        transaction.on_commit(lambda: send_order_placed_notification(order))

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )

    def assign_agent(self, order):
        from accounts.models import User
        # Find agents at this hub with the fewest active orders
        agents = User.objects.filter(
            role='agent',
            district=order.hub
        ).annotate(
            active_orders=Count(
                'assigned_orders',
                filter=Q(assigned_orders__status__in=['pending', 'assigned', 'picked_up', 'dispatched'])
            )
        ).order_by('active_orders', 'id')

        if agents.exists():
            agent = agents.first()
            order.assigned_agent = agent
            order.save()
            return True
        return False


class OrderListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_role:
            return Order.objects.all()
        # Deliberately combines both relationships an agent account can
        # have to orders — assigned to deliver, or the actual customer
        # on their own purchase — rather than picking one exclusively
        # based on account role. An agent buying for themselves would
        # otherwise never see that order in their own order history at
        # all, with no normal way to find it and confirm receipt.
        return Order.objects.filter(
            Q(assigned_agent=user) | Q(customer=user)
        ).distinct()


class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = [IsOrderOwnerOrAgent]


class OrderStatusUpdateView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [IsOrderOwnerOrAgent]
    throttle_classes = [OrderStatusRateThrottle]

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class FlaggedOrdersView(generics.ListAPIView):
    queryset = Order.objects.filter(status='flagged')
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAdmin]
