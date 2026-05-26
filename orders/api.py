"""API viewsets cho Orders và phương thức thanh toán.

Sử dụng DRF `ModelViewSet` cho CRUD nhanh.
"""

from rest_framework import viewsets
from .models import Order, OrderItem, PaymentMethodOption
from .serializers import OrderSerializer, OrderItemSerializer, PaymentMethodOptionSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """CRUD cho `Order` (admin và client có thể dùng tuỳ quyền)."""
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer


class OrderItemViewSet(viewsets.ModelViewSet):
    """CRUD cho `OrderItem`."""
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer


class PaymentMethodOptionViewSet(viewsets.ModelViewSet):
    """CRUD cho `PaymentMethodOption` để cấu hình phương thức thanh toán trong admin."""
    queryset = PaymentMethodOption.objects.all().order_by('name')
    serializer_class = PaymentMethodOptionSerializer
