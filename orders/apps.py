from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    
    # THÊM DÒNG NÀY ĐỂ HIỂN THỊ TIẾNG VIỆT
    verbose_name = 'Quản lý Đơn hàng'