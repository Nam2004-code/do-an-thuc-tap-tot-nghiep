from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

# --- BRANDS ---
class Brand(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True) 
    description = models.TextField(blank=True, null=True) 

    class Meta:
        verbose_name = "Thương hiệu"
        verbose_name_plural = "Thương hiệu"

    def __str__(self):
        return self.name

# --- CATEGORIES ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = "Loại sản phẩm"
        verbose_name_plural = "Loại sản phẩm" 
        
    def __str__(self):
        return self.name

# --- SIZES ---
class Size(models.Model):
    value = models.CharField(max_length=10, unique=True) 

    class Meta:
        verbose_name = "Kích cỡ"
        verbose_name_plural = "Kích cỡ"
    
    def __str__(self):
        return self.value

# --- PRODUCT ---
class Product(models.Model):
    """Mô hình sản phẩm.

    Fields cơ bản: `name`, `brand`, `category`, `sizes`, `price`, `old_price`,... 
    Các helper method dùng trong view và template để tính phần trăm giảm/gia sau giảm.
    """
    name = models.CharField(max_length=200)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ManyToManyField(Category, blank=True, verbose_name="Loại sản phẩm")
    sizes = models.ManyToManyField(Size) 
    
    price = models.IntegerField(
        validators=[MinValueValidator(0)], 
        verbose_name="Giá hiện tại"
    )
    old_price = models.IntegerField(
        null=True, blank=True, 
        validators=[MinValueValidator(0)], 
        verbose_name="Giá cũ (Để trống nếu không giảm giá)"
    )
    
    description = models.TextField(blank=True) 
    image = models.ImageField(
        upload_to='product_images/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'svg', 'gif'])],
        verbose_name="Ảnh đại diện"
    )
    
    stock = models.PositiveIntegerField(default=0, verbose_name="Số lượng tồn kho")
    is_active = models.BooleanField(default=True, verbose_name="Đang kinh doanh")
    stock_status = models.BooleanField(default=True) 

    discount_percent = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Phần trăm giảm giá"
    )

    @property
    def is_on_sale(self):
        return bool(self.old_price and self.old_price > self.price)

    def get_sale_percent(self):
        if self.discount_percent:
            return int(self.discount_percent)
        if self.old_price and self.old_price > self.price:
            percent = ((self.old_price - self.price) / self.old_price) * 100
            return int(percent)
        return 0

    def get_discounted_price(self):
        percent = self.get_sale_percent()
        if percent and percent > 0:
            base = self.old_price if self.old_price else self.price
            discounted = int(base * (100 - percent) / 100)
            return max(discounted, 0)
        return self.price

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"


# --- PRODUCT IMAGES (EXTRA) ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='product_images/extra/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'svg', 'gif'])],
        verbose_name="Ảnh phụ"
    )
    alt_text = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        verbose_name = "Ảnh sản phẩm"
        verbose_name_plural = "Ảnh sản phẩm"


# --- REVIEWS ---
class Review(models.Model):
    RATING_CHOICES = (
        (1, '1 sao'),
        (2, '2 sao'),
        (3, '3 sao'),
        (4, '4 sao'),
        (5, '5 sao'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES, default=5, verbose_name="Số sao")
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"

    def __str__(self):
        return f"{self.user.username} đánh giá {self.product.name} - {self.rating} sao"


    # --- POLICIES ---
class StorePolicy(models.Model):
    title = models.CharField(max_length=100, default="Cấu hình chính sách chung", verbose_name="Tên cấu hình")
    payment_policy = models.TextField(verbose_name="Nội dung Chính sách thanh toán")
    return_policy = models.TextField(verbose_name="Nội dung Chính sách đổi trả")

    class Meta:
        verbose_name = "Chính sách cửa hàng"
        verbose_name_plural = "Chính sách cửa hàng"

    def __str__(self):
        return self.title

# --- SALES/PROMOTIONS ---
class Sale(models.Model):
    """Mô hình chương trình khuyến mãi (Sale).

    Hệ thống hiện chỉ cho phép một chương trình khuyến mãi đang tồn tại.

    - `discount_type`: 'percent' hoặc 'fixed'.
    - `discount_value`: giá trị áp dụng (tùy theo `discount_type`).
    - `sync_product_prices`: đồng bộ giá sản phẩm khi Sale được bật/tắt hoặc thay đổi danh sách sản phẩm.
    """
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_FIXED = 'fixed'
    DISCOUNT_TYPE_CHOICES = (
        (DISCOUNT_PERCENT, 'Giảm theo phần trăm (%)'),
        (DISCOUNT_FIXED, 'Giảm theo số tiền cố định (VND)'),
    )

    title = models.CharField(max_length=120, default='Flash Sale', verbose_name='Tiêu đề chương trình')
    products = models.ManyToManyField(Product, blank=True, related_name='sales', verbose_name='Sản phẩm tham gia')
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_PERCENT,
        verbose_name='Loại giảm giá'
    )
    discount_value = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name='Giá trị giảm',
        help_text='Nếu theo %, nhập từ 1-100. Nếu theo số tiền, nhập số VND cần giảm.'
    )
    start_date = models.DateTimeField(verbose_name='Bắt đầu')
    end_date = models.DateTimeField(verbose_name='Kết thúc')
    active = models.BooleanField(default=True, verbose_name='Kích hoạt')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Chương trình khuyến mãi'
        verbose_name_plural = 'Chương trình khuyến mãi'

    def clean(self):
        super().clean()

        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError({'end_date': 'Thời gian kết thúc phải lớn hơn thời gian bắt đầu.'})

        if self.discount_type == self.DISCOUNT_PERCENT and self.discount_value > 100:
            raise ValidationError({'discount_value': 'Giảm theo phần trăm chỉ được từ 1 đến 100.'})

        conflict_qs = Sale.objects.exclude(pk=self.pk)
        if conflict_qs.exists():
            raise ValidationError('Chỉ được tạo tối đa 1 chương trình khuyến mãi. Hãy sửa chương trình hiện có.')

    def is_currently_active(self):
        """True nếu hiện tại đang trong khoảng start_date..end_date và active=True."""
        now = timezone.now()
        return self.active and self.start_date <= now <= self.end_date

    def _discount_amount(self, base_price):
        """Tính số tiền giảm (VND) dựa trên `discount_type` và `discount_value`."""
        if self.discount_type == self.DISCOUNT_PERCENT:
            return int(base_price * self.discount_value / 100)
        return int(self.discount_value)

    def sync_product_prices(self, previous_product_ids=None):
        """Đồng bộ lại giá sản phẩm khi Sale thay đổi.

        - Nếu sản phẩm trước đó đã có `old_price`, sẽ khôi phục `price` từ `old_price` trước khi áp chương trình mới.
        - Sau đó nếu Sale đang active, áp giá mới lên các sản phẩm tham gia.

        `previous_product_ids` dùng để biết những sản phẩm bị ảnh hưởng khi admin thay đổi danh sách.
        """
        previous_product_ids = set(previous_product_ids or [])
        current_product_ids = set(self.products.values_list('id', flat=True))
        affected_product_ids = previous_product_ids | current_product_ids

        if affected_product_ids:
            for product in Product.objects.filter(id__in=affected_product_ids):
                if product.old_price is not None:
                    product.price = product.old_price
                    product.old_price = None
                    product.discount_percent = None
                    product.save(update_fields=['price', 'old_price', 'discount_percent'])

        if not self.is_currently_active():
            return

        for product in self.products.filter(is_active=True):
            base_price = int(product.price)
            discount_amount = self._discount_amount(base_price)
            new_price = max(base_price - discount_amount, 0)

            if new_price >= base_price:
                continue

            discount_percent = int(round(((base_price - new_price) / base_price) * 100)) if base_price > 0 else 0
            product.old_price = base_price
            product.price = new_price
            product.discount_percent = min(discount_percent, 100)
            product.save(update_fields=['old_price', 'price', 'discount_percent'])

    def __str__(self):
        return f"{self.title} ({self.start_date.date()} - {self.end_date.date()})"


class SalesReport(Product):
    class Meta:
        proxy = True
        verbose_name = "Báo cáo doanh thu"
        verbose_name_plural = "Báo cáo doanh thu"
