from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.db import transaction
from products.models import Product, Size
from .models import Order, OrderItem, PaymentMethodOption


class OrderAdminForm(forms.ModelForm):
    """Form admin cho `Order`.

    - Lấy danh sách `PaymentMethodOption` active làm choice.
    - Thiết lập giá trị mặc định cho hoá đơn tạo nhanh (khách vãng lai).
    """
    payment_method = forms.ChoiceField(label='Phương thức thanh toán')

    class Meta:
        model = Order
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        methods = list(PaymentMethodOption.objects.filter(is_active=True).values_list('code', 'name'))
        if not methods:
            methods = [('COD', 'Thanh toán khi nhận hàng'), ('BANK', 'Chuyển khoản')]

        if self.instance and self.instance.pk and self.instance.payment_method:
            existing_code = self.instance.payment_method
            if existing_code not in {code for code, _ in methods}:
                methods.append((existing_code, f'{existing_code} (không còn active)'))

        self.fields['payment_method'].choices = methods

        if self.instance and self.instance.pk:
            self.initial['payment_method'] = self.instance.payment_method
        elif not self.is_bound:
            # Mặc định cho đơn tạo tại quầy: nhân viên có thể lưu nhanh rồi chỉnh lại nếu cần.
            self.initial.setdefault('full_name', 'Khách vãng lai tại shop')
            self.initial.setdefault('phone', '0000000000')

        self.fields['full_name'].widget.attrs.setdefault('placeholder', 'Khách vãng lai tại shop')
        self.fields['phone'].widget.attrs.setdefault('placeholder', '0000000000')

        self.fields['total_price'].required = False
        self.fields['total_price'].widget.attrs['readonly'] = True
        if not self.initial.get('total_price'):
            self.initial['total_price'] = 0

    def clean_payment_method(self):
        """Xác thực mã phương thức thanh toán nếu có danh sách active."""
        payment_method = (self.cleaned_data.get('payment_method') or '').strip()
        valid_codes = set(PaymentMethodOption.objects.filter(is_active=True).values_list('code', flat=True))
        if valid_codes and payment_method not in valid_codes:
            raise forms.ValidationError('Phương thức thanh toán không hợp lệ.')
        return payment_method

    def clean_total_price(self):
        """Trả về 0 nếu không có giá trị, tránh lỗi khi tính tổng từ inline."""
        total_price = self.cleaned_data.get('total_price')
        if total_price is None:
            return 0
        return total_price


class OrderItemInlineForm(forms.ModelForm):
    """Form cho inline OrderItem trong admin.

    - Hiển thị `price` readonly (giá được lấy từ Product).
    - `size` là ChoiceField dựa trên bảng `Size`.
    """
    price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'readonly': 'readonly'})
    )
    size = forms.ChoiceField(required=True, label='Size')

    class Meta:
        model = OrderItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        size_values = list(Size.objects.order_by('value').values_list('value', flat=True))
        self.fields['size'].choices = [(value, value) for value in size_values]

        if self.instance and self.instance.pk:
            self.initial['size'] = self.instance.size

        product = self.initial.get('product') or getattr(self.instance, 'product', None)
        if product:
            self.initial['price'] = product.price

    def clean(self):
        """Bảo đảm giá luôn bằng giá hiện tại của Product khi lưu."""
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        if product:
            cleaned_data['price'] = product.price
        return cleaned_data


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    form = OrderItemInlineForm
    autocomplete_fields = ['product']
    extra = 1

    class Media:
        js = ('admin/js/order_pos_invoice.js',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin tùy chỉnh cho Order với tính năng xem hóa đơn và endpoint lấy meta sản phẩm.

    - `product_meta_view`: trả về giá và size cho `order_pos_invoice.js`.
    - `invoice_view`: template in hóa đơn.
    - `save_model`/`save_related`: tự động set `return_response` nếu admin thay đổi status và đồng bộ tồn kho khi cần.
    """
    form = OrderAdminForm
    list_display = ['id', 'status', 'display_status', 'full_name', 'phone', 'total_price', 'payment_method', 'invoice_action', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    list_editable = ['status']
    search_fields = ['full_name', 'phone']
    readonly_fields = ['invoice_preview', 'return_reason']
    inlines = [OrderItemInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'product-meta/<int:product_id>/',
                self.admin_site.admin_view(self.product_meta_view),
                name='orders_order_product_meta',
            ),
            path(
                '<int:order_id>/invoice/',
                self.admin_site.admin_view(self.invoice_view),
                name='orders_order_invoice',
            ),
        ]
        return custom_urls + urls

    def product_meta_view(self, request, product_id):
        """API nội bộ admin: trả về `price` và `sizes` cho product.

        Trả về JSON {success, product_id, price, sizes} hoặc lỗi 404.
        """
        product = Product.objects.prefetch_related('sizes').filter(pk=product_id).first()
        if not product:
            return JsonResponse({'success': False, 'error': 'Không tìm thấy sản phẩm'}, status=404)

        sizes = list(product.sizes.order_by('value').values_list('value', flat=True))
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'price': int(product.price or 0),
            'sizes': sizes,
        })

    def invoice_action(self, obj):
        if not obj.pk:
            return '-'
        url = reverse('admin:orders_order_invoice', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Xem hóa đơn</a>', url)

    invoice_action.short_description = 'Hóa đơn'

    def invoice_preview(self, obj):
        if not obj or not obj.pk:
            return 'Lưu đơn hàng trước khi xem hóa đơn.'
        url = reverse('admin:orders_order_invoice', args=[obj.pk])
        return format_html(
            '<p><strong>Trạng thái hiển thị:</strong> {} </p><a class="button" href="{}" target="_blank">Mở hóa đơn</a>',
            obj.display_status,
            url,
        )

    invoice_preview.short_description = 'Xem hóa đơn'

    def display_status(self, obj):
        return obj.display_status

    display_status.short_description = 'Trạng thái'

    def invoice_view(self, request, order_id):
        """Render template in hóa đơn admin cho order cụ thể."""
        order = Order.objects.select_related('user').prefetch_related('orderitem_set__product').filter(pk=order_id).first()
        if not order:
            from django.http import Http404
            raise Http404('Order not found')

        context = dict(
            self.admin_site.each_context(request),
            title=f'Hóa đơn đơn hàng #{order.id}',
            order=order,
            order_items=order.orderitem_set.all(),
            opts=self.model._meta,
        )
        return TemplateResponse(request, 'admin/orders/order/invoice.html', context)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff

    def save_model(self, request, obj, form, change):
        """Ghi order: lưu trạng thái trước khi thay đổi và tự set `return_response` nếu admin thay đổi trạng thái liên quan.

        Mục tiêu: khi admin đánh dấu Returned/Return_Denied/Cancelled, nếu chưa có `return_response` thì tự điền phản hồi mặc định.
        """
        if change and obj.pk:
            previous_order = Order.objects.filter(pk=obj.pk).only('status').first()
            obj._previous_status = previous_order.status if previous_order else obj.status
        else:
            obj._previous_status = None

        if obj.status == 'Returned' and not obj.return_response:
            obj.return_response = 'Yêu cầu đổi/trả của bạn đã được chấp nhận. Shop sẽ liên hệ để xử lý tiếp theo.'
        elif obj.status in ('Return_Denied', 'Cancelled') and not obj.return_response:
            obj.return_response = 'Yêu cầu đổi/trả của bạn đã bị từ chối. Vui lòng liên hệ shop nếu cần thêm hỗ trợ.'

        super().save_model(request, obj, form, change)

    def _sync_product_stock(self, order, delta_sign):
        """Đồng bộ tồn kho khi order thay đổi trạng thái Completed.

        `delta_sign` = -1 khi trừ tồn kho (khi chuyển sang Completed),
        `delta_sign` = +1 khi cộng lại (khi undo Completed).
        """
        with transaction.atomic():
            for item in order.orderitem_set.select_related('product').all():
                product = item.product
                if not product:
                    continue

                current_stock = int(product.stock or 0)
                quantity = int(item.quantity or 0)
                if quantity <= 0:
                    continue

                new_stock = current_stock + (delta_sign * quantity)
                if new_stock < 0:
                    new_stock = 0

                product.stock = new_stock
                product.stock_status = new_stock > 0
                product.save(update_fields=['stock', 'stock_status'])

    def save_related(self, request, form, formsets, change):
        """Sau khi lưu related inlines: tính lại `total_price` và đồng bộ tồn kho nếu cần."""
        super().save_related(request, form, formsets, change)
        order = form.instance
        total = 0
        for item in order.orderitem_set.all():
            if item.product_id and not item.price:
                item.price = item.product.price
                item.save(update_fields=['price'])
            total += int(item.price) * int(item.quantity)

        if order.total_price != total:
            order.total_price = total
            order.save(update_fields=['total_price'])

        previous_status = getattr(order, '_previous_status', None)
        current_status = order.status
        if previous_status != 'Completed' and current_status == 'Completed':
            self._sync_product_stock(order, delta_sign=-1)
        elif previous_status == 'Completed' and current_status != 'Completed':
            self._sync_product_stock(order, delta_sign=1)


@admin.register(PaymentMethodOption)
class PaymentMethodOptionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_editable = ['is_active']
    search_fields = ['code', 'name']
