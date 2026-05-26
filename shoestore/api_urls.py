from rest_framework import routers
from django.urls import path, include

from products.api import (
    BrandViewSet, CategoryViewSet, SizeViewSet, ProductViewSet, ProductImageViewSet,
    ReviewViewSet, StorePolicyViewSet, SaleViewSet,
)
from orders.api import OrderViewSet, OrderItemViewSet, PaymentMethodOptionViewSet
from cart.api import CartViewSet, CartItemViewSet
from users.api import (
    ChatMessageViewSet,
    RegisterAPIView,
    CustomTokenObtainPairView,
    TokenRefreshView,
    LogoutAPIView,
)
from .views import get_response, get_chat_history

router = routers.DefaultRouter()
router.register(r'brands', BrandViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'sizes', SizeViewSet)
router.register(r'products', ProductViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'store-policies', StorePolicyViewSet)

router.register(r'orders', OrderViewSet)
router.register(r'order-items', OrderItemViewSet)
router.register(r'payment-methods', PaymentMethodOptionViewSet)

router.register(r'carts', CartViewSet)
router.register(r'cart-items', CartItemViewSet)

router.register(r'chat-messages', ChatMessageViewSet)

urlpatterns = [
    # Resource CRUD APIs
    path('', include(router.urls)),

    # Auth APIs
    path('auth/register/', RegisterAPIView.as_view(), name='api_auth_register'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='api_auth_token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api_auth_token_refresh'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api_auth_logout'),

    # Business event APIs
    path('events/cart/', include('cart.api_urls')),
    path('events/chat/response/', get_response, name='api_event_chat_response'),
    path('events/chat/history/', get_chat_history, name='api_event_chat_history'),
]
