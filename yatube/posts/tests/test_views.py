import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, Client, TestCase
from django.urls import reverse
from posts.models import Group, Post, Follow

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_to_subscribe = User.objects.create_user(username='auth_subscribe')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-test-slug',
            description='Тестовое описание',
        )
        cls.post_with_group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для оценки работы',
            group=cls.group
        )
        cls.post_without_group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост_2 для оценки работы',
        )
        cls.post_edit_endpoint = 'posts:post_edit'
        cls.post_index_endpoint = 'posts:index'
        cls.post_group_list_endpoint = 'posts:group_list'
        cls.post_profile_endpoint = 'posts:profile'
        cls.post_detail_endpoint = 'posts:post_detail'
        cls.post_create_endpoint = 'posts:post_create'
        cls.post_add_follow_endpoint = 'posts:profile_follow'

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsViewsTests.user)

    def test_posts_urls_uses_correct_template(self):
        """Имена страниц используют соответствующий шаблон."""
        post = Post.objects.get(text='Тестовый пост для оценки работы')
        group = Group.objects.get(title='Тестовая группа')
        user = User.objects.get(username='auth')
        templates_page_names = {
            reverse(PostsViewsTests.post_index_endpoint): 'posts/index.html',
            reverse(PostsViewsTests.post_group_list_endpoint,
                    kwargs={'slug': group.slug}
                    ): 'posts/group_list.html',
            reverse(PostsViewsTests.post_profile_endpoint,
                    kwargs={'username': user.username}): 'posts/profile.html',
            reverse(PostsViewsTests.post_detail_endpoint,
                    kwargs={'post_id': post.id}): 'posts/post_detail.html',
            reverse(PostsViewsTests.post_edit_endpoint,
                    kwargs={'post_id': post.id}): 'posts/create_post.html',
            reverse(
                PostsViewsTests.post_create_endpoint
            ): 'posts/create_post.html',

        }

        for page_name, template in templates_page_names.items():
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name)
                self.assertTemplateUsed(response, template)

    def test_posts_create_correct_context(self):
        """Шаблон create сформирован с правильным
        контекстом.
        """
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }

        response = self.authorized_client.get(
            reverse(PostsViewsTests.post_create_endpoint))

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_posts_edit_correct_context(self):
        """Шаблон post_edit сформирован с правильным
        контекстом.
        """
        post = Post.objects.get(
            text='Тестовый пост для оценки работы')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }

        response = self.authorized_client.get(
            reverse(
                PostsViewsTests.post_edit_endpoint,
                kwargs={'post_id': post.id}))
        is_edit = response.context.get('is_edit')

        self.assertEqual(is_edit, True)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_posts_group_posts_page_show_correct_context(self):
        """  Проверка: на group_list: правильный контекст"""
        group = Group.objects.get(title='Тестовая группа')

        response = self.guest_client.get(
            reverse(
                PostsViewsTests.post_group_list_endpoint,
                kwargs={'slug': group.slug}))
        context_group = response.context['group']

        self.assertEqual(str(context_group), group.title)

    def test_posts_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным
        контекстом.
        """

        post = Post.objects.get(text='Тестовый пост для оценки работы')

        response = self.guest_client.get(
            reverse(PostsViewsTests.post_detail_endpoint,
                    kwargs={'post_id': post.id}))
        context_author = response.context['author']
        context_post_detail = response.context['post_detail']
        context_post_detail_text = context_post_detail.text
        context_post_detail_author = context_post_detail.author
        context_count = response.context['count']

        self.assertEqual(context_author, post.author)
        self.assertEqual(context_post_detail_text, post.text)
        self.assertEqual(context_post_detail_author, post.author)
        self.assertEqual(context_count, post.author.posts.count())

    def test_posts_post_check_presence_index_page(self):
        """Проверяет наличие поста на странице Index."""
        post = Post.objects.first()

        response = self.guest_client.get(
            reverse(PostsViewsTests.post_index_endpoint))
        context_post = response.context['page_obj']

        self.assertIn(post, context_post)

    def test_posts_post_check_presence_group_page(self):
        """Проверяет наличие поста на странице группы, в которую входит пост"""
        post = Post.objects.get(group__title='Тестовая группа')

        response = self.guest_client.get(
            reverse(
                PostsViewsTests.post_group_list_endpoint,
                kwargs={'slug': post.group.slug}))
        context_post = response.context['page_obj']

        self.assertIn(post, context_post)

    def test_posts_post_check_not_presence_group_page(self):
        """
        Проверяет отсутствие поста не входящего в состав группы,
        на странице группы
        """
        group = Group.objects.get(title='Тестовая группа')
        post_2_without_group = Post.objects.get(pk=2)

        response = self.guest_client.get(
            reverse(PostsViewsTests.post_group_list_endpoint,
                    kwargs={'slug': group.slug}))
        context_posts = response.context['page_obj']

        self.assertNotIn(post_2_without_group, context_posts)

    def test_posts_post_check_presence_profile_page(self):
        """
        Проверяет наличие поста на странице пользователя,
         который его создал
         """
        author = User.objects.get(username='auth')
        post = Post.objects.filter(author=author).first()

        response = self.guest_client.get(
            reverse(PostsViewsTests.post_profile_endpoint,
                    kwargs={'username': author.username}))
        context_post = response.context['page_obj']

        self.assertIn(post, context_post)

    def test_posts_post_check_presence_group_detail_page(self):
        """Проверяет на странице post_detail присутствие группы поста"""
        post = Post.objects.get(group__title='Тестовая группа')

        response = self.guest_client.get(
            reverse(PostsViewsTests.post_detail_endpoint,
                    kwargs={'post_id': post.id}))
        context_post_detail = response.context['post_detail']

        self.assertEqual(context_post_detail.group, post.group)

    def test_posts_auth_user_subscribe_check(self):
        """Авторизованный пользователь
        может подписываться на других пользователей и отписываться"""
        user_to_subscribe = User.objects.filter(username='auth_subscribe')
        response = self.authorized_client.get(
            reverse(PostsViewsTests.post_add_follow_endpoint,
                    kwargs={'username': user_to_subscribe}))
        Follow.objects.filter(author=user_to_subscribe)


class PaginatorViewsTest(TestCase):
    """ Для возможности проверки
    пагинатора была сделана выгрузка БД
    в файл json.
     Модель User, где автор leo.
     Модель Post, где есть 37 постов автора leo
     Модель Group, где есть 3 группы, их слаги:
         first_group - 8 постов,
         second_group - 4 поста,
         third_group - 16 постов.
     """
    fixtures = ['db.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.num_page_leo_user = 37
        cls.POST_PER_PAGE = 10
        cls.num_seven_page = 7
        cls.num_six_page = 6

        cls.post_edit_endpoint = 'posts:post_edit'
        cls.post_index_endpoint = 'posts:index'
        cls.post_group_list_endpoint = 'posts:group_list'
        cls.post_profile_endpoint = 'posts:profile'
        cls.post_detail_endpoint = 'posts:post_detail'
        cls.post_create_endpoint = 'posts:post_create'

    def setUp(self):
        self.guest_client = Client()

    def test_posts_profile_page_show_correct_context(self):
        """Шаблон profile сформирован
        с правильным контекстом."""
        user_leo = User.objects.get(username='leo')

        response = self.guest_client.get(
            reverse(PaginatorViewsTest.post_profile_endpoint,
                    kwargs={'username': user_leo.username}))
        context_author = response.context['author']
        context_count = response.context['count']

        self.assertEqual(str(context_author), user_leo.username)
        self.assertEqual(
            context_count, PaginatorViewsTest.num_page_leo_user)

    def test_posts_profile_first_page_contains_ten_records(self):
        """Проверка: на profile leo:
        количество постов на первой странице равно 10.
        """
        user_leo = User.objects.get(username='leo')

        response = self.guest_client.get(
            reverse(PaginatorViewsTest.post_profile_endpoint,
                    kwargs={'username': user_leo.username}))

        self.assertEqual(len(
            response.context['page_obj']),
            PaginatorViewsTest.POST_PER_PAGE)

    def test_posts_profile_fourth_page_contains_three_records(self):
        """Проверка:  profile leo на 4 странице должно быть 7 постов."""
        user_leo = User.objects.get(username='leo')

        response = self.guest_client.get(
            reverse(
                PaginatorViewsTest.post_profile_endpoint,
                kwargs={'username': user_leo.username}) + '?page=4')

        self.assertEqual(len(
            response.context['page_obj']),
            PaginatorViewsTest.num_seven_page)

    def test_posts_index_first_page_contains_ten_records(self):
        """ Проверка: на index: количество постов на
         первой странице равно 10.
         """
        response = self.guest_client.get(
            reverse(
                PaginatorViewsTest.post_index_endpoint))

        self.assertEqual(len(
            response.context['page_obj']),
            PaginatorViewsTest.POST_PER_PAGE)

    def test_posts_index_fourth_page_contains_three_records(self):
        """  Проверка:  index, на 4 странице должно быть 7 постов."""
        response = self.guest_client.get(
            reverse(PaginatorViewsTest.post_index_endpoint) + '?page=4')

        self.assertEqual(len(
            response.context['page_obj']), PaginatorViewsTest.num_seven_page)

    def test_posts_group_posts_page_first_page_contains_ten_records(self):
        """  Проверка: на group_list third_group: количество постов
        на первой странице равно 10.
        """
        third_group = Group.objects.get(slug='third_group')

        response = self.guest_client.get(
            reverse(
                PaginatorViewsTest.post_group_list_endpoint,
                kwargs={'slug': third_group.slug}))

        self.assertEqual(len(
            response.context['page_obj']), PaginatorViewsTest.POST_PER_PAGE)

    def test_posts_group_posts_page_second_page_contains_three_records(self):
        """
        Проверка: на group_list third_group,
         на 2 странице должно быть 6 постов."""
        third_group = Group.objects.get(slug='third_group')

        response = self.guest_client.get(
            reverse(
                PaginatorViewsTest.post_group_list_endpoint,
                kwargs={'slug': third_group.slug}) + '?page=2')

        self.assertEqual(len(
            response.context['page_obj']), PaginatorViewsTest.num_six_page)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsImageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа c картинкой',
            slug='group-test-slug-img',
            description='Тестовое описание с картинкой',
        )
        cls.post_with_image = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для оценки работы',
            group=cls.group,
            image=cls.uploaded
        )
        cls.post_index_endpoint = 'posts:index'
        cls.post_group_list_endpoint = 'posts:group_list'
        cls.post_profile_endpoint = 'posts:profile'
        cls.post_detail_endpoint = 'posts:post_detail'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsImageTests.user)

    def test_posts_post_img_check_presence_context_index_page(self):
        """Проверяет наличие поста с картинкой на странице Index."""
        post = Post.objects.first()

        response = self.authorized_client.get(
            reverse(PostsImageTests.post_index_endpoint))
        post_with_image = response.context['page_obj'][0].image.url

        self.assertEqual(post.image.url, post_with_image)

    def test_posts_post_img_check_presence_context_profile_page(self):
        """Проверяет наличие поста с картинкой на странице profile."""
        author = User.objects.get(username='auth')
        post = Post.objects.filter(author=author).first()

        response = self.authorized_client.get(
            reverse(PostsImageTests.post_profile_endpoint,
                    kwargs={'username': author.username}))
        post_with_image = response.context['page_obj'][0].image.url

        self.assertEqual(post.image.url, post_with_image)

    def test_posts_post_img_check_presence_context_group_list_page(self):
        """Проверяет наличие поста с картинкой на странице group_list."""
        group = Group.objects.get(title='Тестовая группа c картинкой')
        post = Post.objects.filter(group=group).first()

        response = self.authorized_client.get(
            reverse(
                PostsImageTests.post_group_list_endpoint,
                kwargs={'slug': group.slug}))
        post_with_image = response.context['page_obj'][0].image.url

        self.assertEqual(post.image.url, post_with_image)

    def test_posts_post_img_check_presence_context_post_detail_page(self):
        """Проверяет наличие поста с картинкой на странице post_detail"""
        post = Post.objects.get(group__title='Тестовая группа c картинкой')

        response = self.authorized_client.get(
            reverse(PostsImageTests.post_detail_endpoint,
                    kwargs={'post_id': post.id}))
        context_post_detail = response.context['post_detail']

        self.assertEqual(post.image.url, context_post_detail.image.url)
