from django.contrib import admin
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, CharField, Count
from django.db.models.functions import Cast, Substr
from collections import defaultdict
from django.urls import path
from django.template.response import TemplateResponse
from .models import Product, ProductImage, Size, Category, Brand, Review, StorePolicy, SalesReport
from .models import Sale
from orders.models import OrderItem


# --- 2. CẬP NHẬT PRODUCT ADMIN ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  
    verbose_name = "Ảnh phụ"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline] 
    list_display = ('name', 'price', 'old_price', 'discount_percent', 'stock', 'display_categories', 'is_active') 
    list_editable = ('stock', 'price') 
    list_filter = ('category', 'is_active', 'brand')
    search_fields = ('name',)
    filter_horizontal = ('sizes', 'category') 
    readonly_fields = ('old_price', 'discount_percent')

    # Cấu hình hiển thị
    fieldsets = (
        ("Thông tin cơ bản", {
            'fields': ('name', 'brand', 'category', 'price', 'image', 'sizes')
        }),
        ("Khuyến mãi (tự động từ mục Chương trình khuyến mãi)", {
            'classes': ('collapse',),
            'fields': ('old_price', 'discount_percent')
        }),
        ("Quản lý kho hàng", {
            'fields': ('stock', 'is_active', 'stock_status')
        }),
        ("Nội dung mô tả sản phẩm", {
            'classes': ('collapse',), 
            'fields': ('description',),
        }),
    )

    def display_categories(self, obj):
        return ", ".join([cat.name for cat in obj.category.all()])
    display_categories.short_description = 'Loại sản phẩm'

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff


class SalesReportAdmin(admin.ModelAdmin):
    change_list_template = 'admin/products/salesreport/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'revenue-report/',
                self.admin_site.admin_view(self.revenue_report_view),
                name='products_salesreport_revenue_report',
            ),
        ]
        return custom_urls + urls

    def revenue_report_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title='Báo cáo doanh thu',
            sales_chart_data=self._build_revenue_context(),
            opts=self.model._meta,
        )
        return TemplateResponse(request, 'admin/products/salesreport/revenue_report.html', context)

    def _build_revenue_context(self):
        completed_statuses = ['Completed', 'Đã thanh toán', 'Đã thanh toán/Hoàn thành', 'Hoàn thành']
        base_queryset = OrderItem.objects.filter(order__status__in=completed_statuses).select_related('order', 'product')
        month_key_expr = Substr(Cast('order__created_at', output_field=CharField()), 1, 7)

        revenue_expr = ExpressionWrapper(
            F('price') * F('quantity'),
            output_field=DecimalField(max_digits=18, decimal_places=0)
        )

        overall_summary = base_queryset.aggregate(
            total_pairs=Sum('quantity'),
            total_revenue=Sum(revenue_expr),
            total_order_items=Count('id'),
            total_orders=Count('order', distinct=True),
            total_products=Count('product', distinct=True),
        )

        product_summary = (
            base_queryset
            .values('product_id', 'product__name')
            .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(revenue_expr))
            .order_by('-total_quantity', '-total_revenue', 'product__name')
        )

        size_summary = (
            base_queryset
            .values('size')
            .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(revenue_expr))
            .order_by('size')
        )

        product_size_summary = (
            base_queryset
            .values('product_id', 'product__name', 'size')
            .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(revenue_expr))
            .order_by('product__name', 'size')
        )

        recent_items = (
            base_queryset
            .order_by('-order__created_at', 'product__name', 'size')
            .values('order_id', 'order__created_at', 'product_id', 'product__name', 'size', 'quantity', 'price')[:200]
        )

        monthly_totals = (
            base_queryset
            .annotate(month_key=month_key_expr)
            .values('month_key')
            .annotate(total_revenue=Sum(revenue_expr), total_quantity=Sum('quantity'))
            .order_by('month_key')
        )

        product_totals = (
            base_queryset
            .annotate(month_key=month_key_expr)
            .values('month_key', 'product_id', 'product__name')
            .annotate(total_revenue=Sum(revenue_expr), total_quantity=Sum('quantity'))
            .order_by('month_key', '-total_revenue', 'product__name')
        )

        size_totals = (
            base_queryset
            .annotate(month_key=month_key_expr)
            .values('month_key', 'product_id', 'size')
            .annotate(total_quantity=Sum('quantity'))
            .order_by('month_key', 'product_id', 'size')
        )

        month_products = defaultdict(list)
        month_product_index = defaultdict(dict)

        for row in product_totals:
            month_key = row.get('month_key')
            if not month_key:
                continue
            product_payload = {
                'product_id': row['product_id'],
                'product_name': row['product__name'],
                'quantity': int(row['total_quantity'] or 0),
                'revenue': int(row['total_revenue'] or 0),
                'sizes': [],
            }
            month_products[month_key].append(product_payload)
            month_product_index[month_key][row['product_id']] = product_payload

        for row in size_totals:
            month_key = row.get('month_key')
            if not month_key:
                continue
            product_payload = month_product_index.get(month_key, {}).get(row['product_id'])
            if not product_payload:
                continue
            product_payload['sizes'].append({
                'size': row['size'] or 'N/A',
                'quantity': int(row['total_quantity'] or 0),
            })

        months_payload = []
        for row in monthly_totals:
            month_key = row.get('month_key')
            if not month_key:
                continue
            year, month = month_key.split('-')
            months_payload.append({
                'key': month_key,
                'label': f"{month}/{year}",
                'quantity': int(row['total_quantity'] or 0),
                'revenue': int(row['total_revenue'] or 0),
            })

        return {
            'summary': {
                'total_pairs': int(overall_summary.get('total_pairs') or 0),
                'total_revenue': int(overall_summary.get('total_revenue') or 0),
                'total_order_items': int(overall_summary.get('total_order_items') or 0),
                'total_orders': int(overall_summary.get('total_orders') or 0),
                'total_products': int(overall_summary.get('total_products') or 0),
            },
            'months': months_payload,
            'month_products': dict(month_products),
            'overall_products': [
                {
                    'product_id': row['product_id'],
                    'product_name': row['product__name'],
                    'quantity': int(row['total_quantity'] or 0),
                    'revenue': int(row['total_revenue'] or 0),
                }
                for row in product_summary
            ],
            'overall_sizes': [
                {
                    'size': row['size'] or 'N/A',
                    'quantity': int(row['total_quantity'] or 0),
                    'revenue': int(row['total_revenue'] or 0),
                }
                for row in size_summary
            ],
            'product_sizes': [
                {
                    'product_id': row['product_id'],
                    'product_name': row['product__name'],
                    'size': row['size'] or 'N/A',
                    'quantity': int(row['total_quantity'] or 0),
                    'revenue': int(row['total_revenue'] or 0),
                }
                for row in product_size_summary
            ],
            'recent_items': [
                {
                    'order_id': row['order_id'],
                    'created_at': row['order__created_at'].strftime('%d/%m/%Y %H:%M') if row.get('order__created_at') else '',
                    'product_id': row['product_id'],
                    'product_name': row['product__name'],
                    'size': row['size'] or 'N/A',
                    'quantity': int(row['quantity'] or 0),
                    'price': int(row['price'] or 0),
                    'revenue': int((row['price'] or 0) * (row['quantity'] or 0)),
                }
                for row in recent_items
            ],
        }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['sales_chart_data'] = self._build_revenue_context()
        return super().changelist_view(request, extra_context=extra_context)

# Đăng ký mục Chính sách riêng biệt
@admin.register(StorePolicy)
class StorePolicyAdmin(admin.ModelAdmin):
    list_display = ('title',)
    def has_add_permission(self, request):
        return False if StorePolicy.objects.count() >= 1 else True

admin.site.register(Size)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Review)
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('title', 'discount_type', 'discount_value', 'start_date', 'end_date', 'active')
    list_filter = ('active', 'discount_type')
    filter_horizontal = ('products',)
    search_fields = ('title',)
    fieldsets = (
        ('Thông tin chương trình', {
            'fields': ('title', 'active', 'start_date', 'end_date')
        }),
        ('Cấu hình giảm giá', {
            'fields': ('discount_type', 'discount_value')
        }),
        ('Sản phẩm áp dụng', {
            'fields': ('products',)
        }),
    )

    def has_add_permission(self, request):
        if Sale.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change and obj.pk:
            previous_sale = Sale.objects.filter(pk=obj.pk).first()
            obj._previous_product_ids = set(previous_sale.products.values_list('id', flat=True)) if previous_sale else set()
        else:
            obj._previous_product_ids = set()
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sale = form.instance
        sale.sync_product_prices(previous_product_ids=getattr(sale, '_previous_product_ids', set()))


@admin.register(SalesReport)
class SalesReportProxyAdmin(SalesReportAdmin):
    pass