from django.test import TestCase

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from products.models import Product, Size, Brand, Category
from .models import Cart, CartItem


class CartModelTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='alice', password='pass')
		brand = Brand.objects.create(name='B')
		cat = Category.objects.create(name='C')
		size = Size.objects.create(value='42')
		img = SimpleUploadedFile('p.jpg', b'img', content_type='image/jpeg')
		self.product = Product.objects.create(name='P', price=100, image=img, stock=5)
		self.product.sizes.add(size)

	def test_cart_and_items(self):
		cart = Cart.objects.create(user=self.user)
		item = CartItem.objects.create(cart=cart, product=self.product, quantity=2, size='42')
		self.assertEqual(str(cart).startswith('Cart'), True)
		self.assertEqual(str(item), '2 x P')
		self.assertEqual(cart.items.count(), 1)


class CartViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='alice', password='pass')
		brand = Brand.objects.create(name='B')
		cat = Category.objects.create(name='C')
		size = Size.objects.create(value='42')
		img = SimpleUploadedFile('p.jpg', b'img', content_type='image/jpeg')
		self.product = Product.objects.create(name='P', price=100, image=img, stock=5)
		self.product.sizes.add(size)

	def test_add_to_cart_anonymous(self):
		url = f'/cart/add/{self.product.id}/'
		resp = self.client.post(url, {'quantity': 2, 'size': '42'}, follow=True)
		# session should have cart and cart_count
		session = self.client.session
		cart = session.get('cart', {})
		self.assertIn(f"{self.product.id}_42", cart)
		self.assertEqual(cart.get(f"{self.product.id}_42"), 2)
		self.assertEqual(session.get('cart_count'), 2)

	def test_add_to_cart_logged_in_and_ajax(self):
		# login and post as ajax
		logged_in = self.client.login(username='alice', password='pass')
		self.assertTrue(logged_in)
		url = f'/cart/add/{self.product.id}/'
		resp = self.client.post(url, {'quantity': 1, 'size': '42'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		# should return JSON with cart_count
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		self.assertTrue(data.get('status') == 'success' or data.get('cart_count') is not None)
		session = self.client.session
		self.assertEqual(session.get('cart_count'), 1)
