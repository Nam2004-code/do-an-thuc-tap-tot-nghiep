from django.urls import path
from . import views

app_name = 'orders'  # Dòng này cực kỳ quan trọng

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('create/', views.order_create, name='order_create'),
    path('success/', views.order_success, name='order_success'),
]