from rest_framework import serializers
from .models import Product


class ProductListSerializer(serializers.ModelSerializer):
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock', 'category', 'image', 'is_in_stock', 'created_at']


class ProductAdminSerializer(serializers.ModelSerializer):
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'cost_price', 'stock', 'category', 'image', 'is_in_stock', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
