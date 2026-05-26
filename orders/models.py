from django.db import models
from products.models import Product


class PaymentMethodOption(models.Model):
    """Mã phương thức thanh toán lưu trong DB.

    Trường `code`: mã dùng nội bộ (ví dụ 'COD', 'BANK').
    Trường `name`: tên hiển thị.
    Trường `is_active`: bật/tắt phương thức.
    """
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Phương thức thanh toán"
        verbose_name_plural = "Phương thức thanh toán"


class Order(models.Model):
    """Mô hình đơn hàng chính.

    - `can_return`: property boolean, cho biết đơn hàng còn trong thời hạn đổi/trả (7 ngày) và đã ở trạng thái 'Completed'.
    - `display_status`: trả về chuỗi trạng thái hiển thị (tách 'Đã thanh toán' và 'Hoàn thành').
    - `return_status_message`: trả về thông điệp phản hồi liên quan đến đổi/trả (khi admin đã phản hồi).
    """
    STATUS_CHOICES = (
        ('Pending', 'Chờ thanh toán'),
        ('Processing', 'Đang xử lý'),
        ('Completed', 'Đã thanh toán/Hoàn thành'),
        ('Return_Requested', 'Yêu cầu đổi/trả'),
        ('Returned', 'Đã đổi/trả'),
        ('Return_Denied', 'Từ chối đổi/trả'),
        ('Cancelled', 'Đã hủy'),
    )
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    payment_method = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=12, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    return_reason = models.TextField(blank=True, null=True, verbose_name="Lý do đổi/trả")
    return_response = models.TextField(blank=True, null=True, verbose_name="Phản hồi đổi/trả")

    @property
    def can_return(self):
        """True nếu đơn đã hoàn thành và trong vòng 7 ngày kể từ `created_at`.

        Sử dụng để bật/tắt UI đổi trả cho khách.
        """
        from django.utils import timezone
        import datetime
        if self.status == 'Completed':
            now = timezone.now()
            return (now - self.created_at) <= datetime.timedelta(days=7)
        return False

    @property
    def display_status(self):
        """Trả về chuỗi trạng thái thân thiện với người dùng.

        Nếu `status` là 'Completed', tách thành 'Đã thanh toán' khi phương thức là chuyển khoản.
        """
        if self.status == 'Completed':
            if (self.payment_method or '').upper() == 'BANK':
                return 'Đã thanh toán'
            return 'Hoàn thành'
        return self.get_status_display()

    @property
    def return_status_message(self):
        """Thông điệp phản hồi cho yêu cầu đổi/trả.

        Nếu admin đã chấp nhận/ từ chối sẽ hiển thị `return_response`, ngược lại trả về mặc định phù hợp.
        """
        if self.status == 'Returned':
            return self.return_response or 'Yêu cầu đổi/trả của bạn đã được chấp nhận.'
        if self.status in ('Return_Denied', 'Cancelled'):
            return self.return_response or 'Yêu cầu đổi/trả của bạn đã bị từ chối.'
        return self.return_response

    def __str__(self):
        return f"Order #{self.id}"

    class Meta:
        verbose_name = "Đơn hàng tại shop"
        verbose_name_plural = "Đơn hàng tại shop"


class OrderItem(models.Model):
    """Chi tiết từng dòng sản phẩm trong đơn hàng.

    - `get_cost()`: trả về thành tiền (price * quantity).
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10)

    def get_cost(self):
        """Tính tổng tiền của dòng: giá * số lượng.

        Trả về Decimal.
        """
        return self.price * self.quantity

    class Meta:
        verbose_name = "Chi tiết đơn hàng"
        verbose_name_plural = "Chi tiết đơn hàng"