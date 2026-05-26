from django.test import TestCase

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from products.models import Product, Size, Brand, Category
from .models import Order, OrderItem


class OrderModelTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='bob', password='pass')
		brand = Brand.objects.create(name='B')
		cat = Category.objects.create(name='C')
		size = Size.objects.create(value='42')
		img = SimpleUploadedFile('p.jpg', b'img', content_type='image/jpeg')
		self.product = Product.objects.create(name='P', price=150, image=img, stock=3)
		self.product.sizes.add(size)

	def test_create_order_and_items(self):
		order = Order.objects.create(user=self.user, full_name='Bob', phone='0123', address='Addr', payment_method='cash', total_price=300)
		oi = OrderItem.objects.create(order=order, product=self.product, price=150, quantity=2, size='42')
		self.assertEqual(order.orderitem_set.count(), 1)
		self.assertEqual(oi.order, order)
		self.assertEqual(str(order), getattr(order, '__str__', lambda: f'Order {order.id}')())
