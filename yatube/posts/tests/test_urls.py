from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user_with_posts = User.objects.create_user(username = 'auth')
		cls.user_without_posts = User.objects.create_user(username = 'auth_2')
		cls.group = Group.objects.create(
			title = 'Тестовая группа',
			slug = 'group-test-slug',
			description = 'Тестовое описание',
		)
		cls.post = Post.objects.create(
			author = cls.user_with_posts,
			text = 'Тестовый пост для оценки работы',
		)
		cls.post_edit_url = f'/posts/{PostsURLTests.post.id}/edit/'
		cls.post_create_url = '/create/'
		cls.post_detail_url = f'/posts/{PostsURLTests.post.id}/'
		cls.post_detail_endpoint = 'posts:post_detail'
		cls.post_comment_url = f'/posts/{PostsURLTests.post.id}/comment/'
	def setUp(self):
		self.guest_client = Client()

		self.user_with_posts = User.objects.get(username = 'auth')
		self.authorized_client_with_posts = Client()
		self.authorized_client_with_posts.force_login(self.user_with_posts)

		self.user_without_posts = User.objects.get(username = 'auth_2')
		self.authorized_client_without_posts = Client()
		self.authorized_client_without_posts.force_login(
			self.user_without_posts)

	def test_posts_urls_uses_correct_template(self):
		"""URL-адрес использует соответствующий шаблон."""
		templates_url_names = {
			'/': 'posts/index.html',
			f'/group/{PostsURLTests.group.slug}/': 'posts/group_list.html',
			f'/profile/{PostsURLTests.user_with_posts.username}/':
				'posts/profile.html',
			PostsURLTests.post_detail_url: 'posts/post_detail.html',
			PostsURLTests.post_edit_url: 'posts/create_post.html',
			PostsURLTests.post_create_url: 'posts/create_post.html',
		}

		for address, template in templates_url_names.items():
			with self.subTest(address = address):
				response = self.authorized_client_with_posts.get(address)
				self.assertTemplateUsed(response, template)

	def test_posts_correct_response_authorize_user(self):
		"""
		Авторизованный пользователь имеет доступ на странички:
		Главная
		Страница группы
		Страница профиля
		Страница поста - просмотр
		Страница поста - создание
		Страница поста созданного - изменение
		Добавление комментария
		"""
		urls = (
			f'/group/{PostsURLTests.group.slug}/',
			'/',
			f'/profile/{PostsURLTests.user_with_posts.username}/',
			PostsURLTests.post_detail_url,
			PostsURLTests.post_create_url,
			PostsURLTests.post_edit_url,
		)

		for url in urls:
			with self.subTest(url = url):
				response = self.authorized_client_with_posts.get(url)
				self.assertEqual(response.status_code, HTTPStatus.OK)

	def test_posts_redirect_anonymous_on_login(self):
		"""
		Страницы в переменной login_required_urls перенаправят
		анонимного пользователя на страницу логина.
		Изменять пост
		Создавать пост
		Писать комментарии
		"""
		login_required_urls = (
			PostsURLTests.post_edit_url,
			PostsURLTests.post_create_url,
			PostsURLTests.post_comment_url,
		)

		for login_required_url in login_required_urls:
			with self.subTest(login_required_url = login_required_url):
				response = self.guest_client.get(
					login_required_url, follow = True)
				self.assertRedirects(
					response, f'/auth/login/?next={login_required_url}')


	def test_posts_redirect_not_author_cannot_edit(self):
		"""
		Не автор поста не имеет доступ к редактированию, перенаправляется
		на страницу поста.
		"""
		post = Post.objects.get(text = 'Тестовый пост для оценки работы')

		login_required_edit_url = PostsURLTests.post_edit_url
		response = self.authorized_client_without_posts.get(
			login_required_edit_url, follow = True)

		self.assertRedirects(
			response, reverse(
				PostsURLTests.post_detail_endpoint,
				kwargs = {'post_id': post.id}))

	def test_posts_not_existing_url_404_status(self):
		"""Несуществующая страница выдает 404."""
		response = self.guest_client.get(
			f'{PostsURLTests.post_detail_url}/post')

		self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
