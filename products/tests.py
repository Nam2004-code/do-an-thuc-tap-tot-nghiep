from django.shortcuts import redirect
from django.contrib import messages

# ==========================================
# QUẢN LÝ SẢN PHẨM (THÊM, SỬA, XÓA)
# ==========================================
def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm sản phẩm mới thành công!')
            return redirect('products:product_list')
    else:
        form = ProductForm()
    
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Thêm Sản Phẩm Mới'})

def update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật {product.name} thành công!')
            return redirect('products:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
        
    return render(request, 'products/product_form.html', {'form': form, 'title': 'Cập Nhật Sản Phẩm', 'product': product})

def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Đã xóa sản phẩm {product_name}.')
        return redirect('products:product_list')
        
    return render(request, 'products/product_confirm_delete.html', {'product': product})


from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Product, Brand, Category, Size, StorePolicy


class ProductModelTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='Test Brand')
        self.cat = Category.objects.create(name='Sneakers')
        self.size = Size.objects.create(value='42')
        img = SimpleUploadedFile('test.jpg', b'fake-image-bytes', content_type='image/jpeg')
        self.product = Product.objects.create(
            name='Test Shoe',
            brand=self.brand,
            price=800,
            old_price=1000,
            description='Nice shoe',
            image=img,
            stock=10,
            is_active=True,
        )
        self.product.category.add(self.cat)
        self.product.sizes.add(self.size)

    def test_is_on_sale_true(self):
        self.assertTrue(self.product.is_on_sale)

    def test_get_sale_percent(self):
        self.assertEqual(self.product.get_sale_percent(), 20)

    def test_str_methods(self):
        self.assertEqual(str(self.brand), 'Test Brand')
        self.assertEqual(str(self.cat), 'Sneakers')
        self.assertEqual(str(self.size), '42')
        self.assertEqual(str(self.product), 'Test Shoe')


class StorePolicyTests(TestCase):
    def test_storepolicy_str(self):
        sp = StorePolicy.objects.create(title='Policy', payment_policy='Pay', return_policy='Return')
        self.assertEqual(str(sp), 'Policy')


class ProductCrudModelTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='BrandX')
        self.cat = Category.objects.create(name='Casual')
        self.size = Size.objects.create(value='40')

    def test_create_update_delete_product(self):
        img = SimpleUploadedFile('p.jpg', b'img', content_type='image/jpeg')
        p = Product.objects.create(name='CRUD Shoe', brand=self.brand, price=500, image=img, stock=3)
        p.category.add(self.cat)
        p.sizes.add(self.size)

        # Verify create
        self.assertTrue(Product.objects.filter(name='CRUD Shoe').exists())

        # Update
        p.price = 450
        p.save()
        p2 = Product.objects.get(name='CRUD Shoe')
        self.assertEqual(p2.price, 450)

        # Delete
        p.delete()
        self.assertFalse(Product.objects.filter(name='CRUD Shoe').exists())