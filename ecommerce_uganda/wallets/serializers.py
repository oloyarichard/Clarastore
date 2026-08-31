from django.db import models
from rest_framework import serializers

from accounts.models import User
from .models import AgentCommission, TopUpRequest, Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'created_at', 'updated_at']
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'type', 'amount', 'balance_after', 'reference', 'created_at']
        read_only_fields = fields


class AgentCommissionSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order_item.order.id', read_only=True)
    product_name = serializers.CharField(source='order_item.product.name', read_only=True)

    class Meta:
        model = AgentCommission
        fields = ['id', 'order_id', 'product_name', 'profit_amount', 'commission_amount', 'created_at']
        read_only_fields = fields


class TopUpRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopUpRequest
        fields = ['id', 'provider', 'phone_number', 'amount', 'status', 'created_at', 'updated_at']
        read_only_fields = fields


class GatewayTopUpSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    phone_number = serializers.CharField()
    # Defaults to GosentePay, which routes to MTN or Airtel internally
    # based on the phone number — no need to guess the network
    # ourselves anymore. mtn_momo/airtel_money remain selectable for
    # the old direct-integration path, which still exists but isn't
    # the default now.
    provider = serializers.ChoiceField(choices=TopUpRequest.PROVIDER_CHOICES, required=False)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate(self, attrs):
        if not attrs.get('provider'):
            attrs['provider'] = 'gosentepay'
        return attrs


class AgentTopUpSerializer(serializers.Serializer):
    customer_identifier = serializers.CharField(help_text="Customer's email or phone number")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate_customer_identifier(self, value):
        try:
            customer = User.objects.get(
                models.Q(email=value) | models.Q(phone=value),
                role='customer'
            )
        except User.DoesNotExist:
            raise serializers.ValidationError("Customer not found.")
        except User.MultipleObjectsReturned:
            raise serializers.ValidationError("Multiple customers matched — use a unique identifier.")
        return customer

    def validate(self, attrs):
        attrs['customer'] = attrs.pop('customer_identifier')
        return attrs
