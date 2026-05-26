"""Serializers cho API Order và PaymentMethodOption.

Các serializer này dùng cho endpoint admin/API nội bộ và mobile client.
"""

from rest_framework import serializers
from .models import Order, OrderItem, PaymentMethodOption


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'product', 'price', 'quantity', 'size']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
    display_status = serializers.CharField(read_only=True)
    can_return = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'full_name',
            'phone',
            'address',
            'payment_method',
            'total_price',
            'created_at',
            'status',
            'display_status',
            'return_reason',
            'return_response',
            'can_return',
            'items',
        ]


class PaymentMethodOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethodOption
        fields = ['id', 'code', 'name', 'is_active']
