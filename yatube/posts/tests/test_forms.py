import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для оценки работы',
        )
        cls.post_profile_endpoint = 'posts:profile'
        cls.post_create_endpoint = 'posts:post_create'
        cls.post_detail_endpoint = 'posts:post_detail'
        cls.post_edit_endpoint = 'posts:post_edit'
        cls.post_add_comment_endpoint = 'posts:add_comment'

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsFormsTests.user)

    def test_posts_post_create(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый заголовок форма',
            'group': Group.objects.get(title='Тестовая группа').id
        }

        response = self.authorized_client.post(
            reverse(PostsFormsTests.post_create_endpoint),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse(PostsFormsTests.post_profile_endpoint,
                    kwargs={'username': PostsFormsTests.user}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=PostsFormsTests.user,
                text='Тестовый заголовок форма',
                group=PostsFormsTests.group
            ).exists()
        )

    def test_posts_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        post = Post.objects.get(pk=1)
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый заголовок форма_изменили',
            'group': Group.objects.get(title='Тестовая группа').id
        }

        response = self.authorized_client.post(
            reverse(PostsFormsTests.post_edit_endpoint,
                    kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response, reverse(
                PostsFormsTests.post_detail_endpoint,
                kwargs={'post_id': post.id}))
        self.assertTrue(
            Post.objects.get(
                pk=post.id).text == 'Тестовый заголовок форма_изменили'
        )
        self.assertTrue(
            Post.objects.filter(
                author=PostsFormsTests.user,
                text='Тестовый заголовок форма_изменили',
                group=PostsFormsTests.group
            ).exists()
        )
        self.assertEqual(Post.objects.count(), posts_count)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsCreateImageFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа c картинкой',
            slug='group-test-slug-img',
            description='Тестовое описание с картинкой',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.post_profile_endpoint = 'posts:profile'
        cls.post_create_endpoint = 'posts:post_create'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsCreateImageFormTests.user)

    def test_posts_create_post_with_image(self):
        """Тестируется форма создание поста с добавлением изображения."""
        posts_count = Post.objects.count()
        group = Group.objects.get(title='Тестовая группа c картинкой')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=PostsCreateImageFormTests.small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост для оценки работы с картинкой',
            'group': group.id,
            'image': uploaded
        }

        response = self.authorized_client.post(
            reverse(PostsCreateImageFormTests.post_create_endpoint),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse(
            PostsCreateImageFormTests.post_profile_endpoint,
            kwargs={'username': PostsCreateImageFormTests.user}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост для оценки работы с картинкой',
                group=group,
                image='posts/small.gif'
            ).exists())
