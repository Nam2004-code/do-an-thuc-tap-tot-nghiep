from django.test import TestCase

from django.contrib.auth.models import User
from .models import ChatMessage
from django.contrib import auth
from django.urls import reverse


class ChatMessageTests(TestCase):
	def test_chatmessage_str_and_ordering(self):
		u = User.objects.create_user(username='u1')
		m1 = ChatMessage.objects.create(user=u, message='Hello', is_bot=False)
		m2 = ChatMessage.objects.create(user=None, message='Bot reply', is_bot=True)
		# ordering by created_at defined in Meta
		qs = list(ChatMessage.objects.all())
		self.assertEqual(qs[0].message, 'Hello')
		self.assertIn('Hello', str(m1))


class AuthTests(TestCase):
	def setUp(self):
		self.username = 'testuser'
		self.password = 'StrongPass123!'
		self.email = 'test@example.com'
		self.user = User.objects.create_user(username=self.username, password=self.password, email=self.email)

	def test_login_success(self):
		resp = self.client.post(reverse('login'), {'username': self.username, 'password': self.password})
		self.assertRedirects(resp, reverse('home'))
		user = auth.get_user(self.client)
		self.assertTrue(user.is_authenticated)

	def test_login_failure(self):
		resp = self.client.post(reverse('login'), {'username': self.username, 'password': 'wrong'})
		self.assertEqual(resp.status_code, 200)
		user = auth.get_user(self.client)
		self.assertFalse(user.is_authenticated)

	def test_logout(self):
		# log the user in via the test client then call logout view
		self.client.login(username=self.username, password=self.password)
		resp = self.client.get(reverse('logout'))
		self.assertRedirects(resp, reverse('home'))
		user = auth.get_user(self.client)
		self.assertFalse(user.is_authenticated)

	def test_register_success(self):
		username = 'newuser'
		email = 'newuser@example.com'
		password = 'AnotherStrong1!'
		resp = self.client.post(reverse('register'), {
			'username': username,
			'email': email,
			'password': password,
			'confirm_password': password,
		})
		self.assertRedirects(resp, reverse('login'))
		self.assertTrue(User.objects.filter(username=username, email=email).exists())

	def test_register_password_mismatch(self):
		resp = self.client.post(reverse('register'), {
			'username': 'x',
			'email': 'x@example.com',
			'password': 'pw1',
			'confirm_password': 'pw2',
		})
		# on failure the view renders register page (redirect to register), but implementation redirects back to 'register'
		# The view uses messages and returns redirect('register') on many errors; ensure user not created
		self.assertFalse(User.objects.filter(username='x').exists())


class UserCrudTests(TestCase):
	def test_create_update_delete_user_model(self):
		# Create
		u = User.objects.create_user(username='cruduser', password='pw123', email='crud@example.com')
		self.assertTrue(User.objects.filter(username='cruduser').exists())

		# Update
		u.email = 'updated@example.com'
		u.save()
		u2 = User.objects.get(username='cruduser')
		self.assertEqual(u2.email, 'updated@example.com')

		# Delete
		u.delete()
		self.assertFalse(User.objects.filter(username='cruduser').exists())
