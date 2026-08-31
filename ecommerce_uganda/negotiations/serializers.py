from rest_framework import serializers

from .models import NegotiationOffer, NegotiationSession


class NegotiationOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = NegotiationOffer
        fields = ['id', 'turn_type', 'amount', 'decision', 'message', 'created_at']
        read_only_fields = fields


class NegotiationSessionSerializer(serializers.ModelSerializer):
    offers = NegotiationOfferSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = NegotiationSession
        fields = [
            'id', 'product', 'product_name', 'status',
            'agreed_price', 'agreed_at', 'expires_at',
            'created_at', 'offers',
        ]
        read_only_fields = fields


class StartNegotiationSerializer(serializers.Serializer):
    # Without an upper bound here, an absurdly large integer used as a
    # lookup key crashes the database layer directly (confirmed: the
    # exact same OverflowError as the cart's quantity/product_id
    # fields) instead of failing validation cleanly.
    product_id = serializers.IntegerField(max_value=2147483647)

    def validate_product_id(self, value):
        from catalog.models import Product
        try:
            product = Product.objects.get(pk=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
        if not product.is_in_stock:
            raise serializers.ValidationError("This product is out of stock.")
        return product


class SubmitOfferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Offer must be a positive amount.")
        return value
