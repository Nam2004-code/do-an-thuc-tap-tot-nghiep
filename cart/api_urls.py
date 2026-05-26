from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_get_cart, name='api_get_cart'),
    path('add/', views.api_add_to_cart, name='api_add_to_cart'),
    path('update/', views.api_update_cart, name='api_update_cart'),
    path('remove/', views.api_remove_from_cart, name='api_remove_from_cart'),
    path('checkout/', views.api_checkout, name='api_checkout'),
]
