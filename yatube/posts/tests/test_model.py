from django.contrib.auth import get_user_model
from django.test import TestCase
from posts.models import Group, Post

User = get_user_model()


class PostsModelsTest(TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = User.objects.create_user(username = 'auth')
		cls.group = Group.objects.create(
			title = 'Тестовая группа',
			slug = 'Тестовый слаг',
			description = 'Тестовое описание',
		)
		cls.post = Post.objects.create(
			author = cls.user,
			text = 'Тестовый пост для оценки работы',
		)

	def test_model_post_has_correct_object_name(self):
		"""Проверяем, что у модели post корректно работает __str__."""
		post = Post.objects.get(text = 'Тестовый пост для оценки работы')
		post_text = post.text

		self.assertEqual(str(post), post_text[:15])

	def test_model_group_has_correct_object_name(self):
		"""Проверяем, что у модели group корректно работает __str__."""
		group = Group.objects.get(title = 'Тестовая группа')
		group_title = group.title

		self.assertEqual(str(group), group_title)

	def test_model_post_verbose_name(self):
		"""Verbose_name в полях совпадает с ожидаемым."""
		post = Post.objects.get(text = 'Тестовый пост для оценки работы')
		field_verboses = {
			'text': 'Текст поста',
			'pub_date': 'Дата публикации',
			'author': 'Автор',
			'group': 'Группа',
		}

		for value, expected in field_verboses.items():
			with self.subTest(value = value):
				self.assertEqual(
					post._meta.get_field(value).verbose_name, expected)

	def test_model_post_help_text(self):
		"""Help_text в полях совпадает с ожидаемым."""
		post = PostsModelsTest.post
		field_verboses = {
			'text': 'Введите текст поста',
			'group': 'Группа, к которой будет относиться пост',
		}

		for value, expected in field_verboses.items():
			with self.subTest(value = value):
				self.assertEqual(
					post._meta.get_field(value).help_text, expected)
