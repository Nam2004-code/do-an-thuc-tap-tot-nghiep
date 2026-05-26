from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    # Giữ cả 2 name để không lỗi các trang cũ
    path('add/<int:product_id>/', views.add_to_cart, name='cart_add'), 
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    
    path('update/', views.update_cart, name='update_cart_query'),
    path('update/<str:item_key>/<str:action>/', views.update_cart, name='update_cart'),
    path('remove/', views.remove_from_cart, name='remove_from_cart_query'),
    path('remove/<str:item_key>/', views.remove_from_cart, name='remove_from_cart'),
    
    path('checkout/', views.checkout, name='checkout'),
]