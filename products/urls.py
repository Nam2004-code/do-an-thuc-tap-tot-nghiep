from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('search/', views.search_products, name='search'), 
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('order-history/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/return/', views.request_return, name='request_return'),
    path('return-eligible/', views.return_eligible_orders, name='return_eligible_orders'),
]