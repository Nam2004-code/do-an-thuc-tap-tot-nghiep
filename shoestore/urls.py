"""
URL configuration for shoestore project.
"""
from django.contrib import admin
from django.urls import path, include
from . import views  # Giữ nguyên để dùng cho các trang như help_page
from products import views as product_views  # ĐÃ THÊM: Import views từ app products sang

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ĐÃ SỬA: Gọi hàm home từ product_views
    path('', product_views.home, name='home'),
    
    # Trang trợ giúp 
    path('help/', views.help_page, name='help'), 
    
    # Chính sách đổi trả
    path('return-policy/', views.return_policy_page, name='return_policy'),
    
    # Chính sách bảo hành
    path('warranty-policy/', views.warranty_policy_page, name='warranty_policy'),
    
    # Liên hệ
    path('contact/', views.contact_page, name='contact'),
    
    # ĐÃ SỬA: Gọi hàm sale_page từ product_views
    path('sale/', product_views.sale_page, name='sale'),
    
    # Kết nối tới App products
    path('products/', include('products.urls')), 
    # Legacy chatbot API (backward compatibility)
    path('api/get_response/', views.get_response, name='get_response'),
    path('api/get_chat_history/', views.get_chat_history, name='get_chat_history'),
    
    # KẾT NỐI TỚI APP USERS 
    path('users/', include('users.urls')),
    
    path('cart/', include('cart.urls')), 
    # Legacy cart event APIs (backward compatibility)
    path('api/cart/', include('cart.api_urls')),
    # Legacy central API router
    path('api/', include('shoestore.api_urls')),
    # Versioned API (recommended)
    path('api/v1/', include('shoestore.api_urls')),
    path('orders/', include('orders.urls', namespace='orders')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)