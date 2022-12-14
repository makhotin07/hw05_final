import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, Follow, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_to_subscribe = User.objects.create_user(
            username='auth_to_subscribe')
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
        cls.post_delete_follow_endpoint = 'posts:profile_unfollow'
        cls.post_follow_index_endpoint = 'posts:follow_index'
        cls.post_add_comment_endpoint = 'posts:add_comment'

    def setUp(self):
        cache.clear()
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

    def test_posts_can_follow_auth_user(self):
        """Авторизованный пользователь может подписываться"""
        user_follower_client = self.authorized_client
        follower_count = Follow.objects.count()
        user_follower = User.objects.get(username='auth')
        user_to_subscribe = User.objects.get(username='auth_to_subscribe')
        Post.objects.create(
            author=user_to_subscribe, text='Пост для проверки подписки')

        response_subscribe = user_follower_client.get(
            reverse(PostsViewsTests.post_add_follow_endpoint,
                    kwargs={'username': user_to_subscribe.username}))

        self.assertEqual(Follow.objects.count(), follower_count + 1)
        self.assertRedirects(response_subscribe, reverse(
            PostsViewsTests.post_follow_index_endpoint))
        self.assertTrue(Follow.objects.filter(
            user=user_follower, author=user_to_subscribe).exists())

    def test_posts_can_unfollow_auth_user(self):
        """Авторизованный пользовать может отписываться"""
        user_follower_client = self.authorized_client
        follower_count = Follow.objects.count()
        user_follower = User.objects.get(username='auth')
        user_to_subscribe = User.objects.get(username='auth_to_subscribe')
        Post.objects.create(
            author=user_to_subscribe, text='Пост для проверки подписки')

        response_unfollow = user_follower_client.get(
            reverse(PostsViewsTests.post_delete_follow_endpoint,
                    kwargs={'username': user_to_subscribe.username}))

        self.assertEqual(
            Follow.objects.count(), follower_count)
        self.assertRedirects(
            response_unfollow, reverse(
                PostsViewsTests.post_follow_index_endpoint))
        self.assertFalse(
            Follow.objects.filter(
                user=user_follower, author=user_to_subscribe).exists())

    def test_posts_cannot_follow_guest_user(self):
        """Не авторизованный пользователь не может подписываться"""
        guest_client = self.guest_client
        user_to_subscribe = User.objects.get(username='auth_to_subscribe')
        follower_count = Follow.objects.count()
        link_follow_add = reverse(PostsViewsTests.post_add_follow_endpoint,
                                  kwargs={
                                      'username': user_to_subscribe.username})

        response = guest_client.get(link_follow_add)

        self.assertRedirects(
            response, f'/auth/login/?next={link_follow_add}')
        self.assertEqual(
            Follow.objects.count(), follower_count)

    def test_posts_follower_see_posts_if_subscribed(self):
        """Авторизованный пользователь видит посты того, на кого подписан"""
        user_follower_client = self.authorized_client
        user_follower = User.objects.get(username='auth')
        user_to_subscribe = User.objects.get(username='auth_to_subscribe')
        Post.objects.create(
            author=user_to_subscribe, text='Пост для проверки подписки')

        user_follower_client.get(
            reverse(PostsViewsTests.post_add_follow_endpoint,
                    kwargs={'username': user_to_subscribe.username}))
        follow_page_response = user_follower_client.get(
            reverse(PostsViewsTests.post_follow_index_endpoint))
        posts_user_to_subscribe = Post.objects.filter(
            author__following__user=user_follower).first()
        context_posts = follow_page_response.context['page_obj'].object_list

        self.assertIn(posts_user_to_subscribe, context_posts)

    def test_posts_follower_do_not_see_posts_if_not_subscribed(self):
        """Авторизованный пользователь не видит
        посты того, на кого не подписан"""
        user_not_follower_client = self.authorized_client
        user_not_to_subscribe = User.objects.get(
            username='auth_to_subscribe')
        Post.objects.create(
            author=user_not_to_subscribe, text='Пост для проверки подписки')

        follow_page_response = user_not_follower_client.get(
            reverse(PostsViewsTests.post_follow_index_endpoint))
        posts_user_to_subscribe = Post.objects.filter(
            author=user_not_to_subscribe).first()
        context_posts = follow_page_response.context['page_obj'].object_list

        self.assertNotIn(posts_user_to_subscribe, context_posts)

    def test_posts_post_check_cache_index_page(self):
        """Проверяет работу кэша index страницы объекта page_obj."""
        post = Post.objects.filter(
            text='Тестовый пост для оценки работы').first()

        response_before_cache = self.guest_client.get(
            reverse(PostsViewsTests.post_index_endpoint))
        post.delete()
        response_cached = self.guest_client.get(
            reverse(PostsViewsTests.post_index_endpoint))
        cache.clear()
        response_cleared_cache = self.guest_client.get(
            reverse(PostsViewsTests.post_index_endpoint))

        self.assertEqual(
            response_before_cache.content, response_cached.content)
        self.assertNotEqual(
            response_cached.content, response_cleared_cache.content)

    def test_post_authorize_user_can_comment(self):
        """Авторизованный пользователь может создавать комментарий"""
        post = Post.objects.get(text='Тестовый пост для оценки работы')
        comment_count = Comment.objects.count()
        text_comment = 'Тестовый комментарий'
        form_data = {
            'text': text_comment,
        }

        response = self.authorized_client.post(
            reverse(PostsViewsTests.post_add_comment_endpoint,
                    kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response, reverse(
                PostsViewsTests.post_detail_endpoint,
                kwargs={'post_id': post.id}))
        self.assertTrue(
            Comment.objects.get(
                pk=post.id).text == text_comment
        )
        self.assertTrue(
            Comment.objects.filter(
                author=PostsViewsTests.user,
                text=text_comment,
                post=post
            ).exists()
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_post_guest_user_cannot_comment(self):
        """Не авторизованный пользователь не может оставлять комментарии"""
        post = Post.objects.get(text='Тестовый пост для оценки работы')
        comment_count = Comment.objects.count()
        text_comment = 'Тестовый комментарий'
        url_comment_add = reverse(PostsViewsTests.post_add_comment_endpoint,
                                  kwargs={'post_id': post.id})
        form_data = {
            'text': text_comment,
        }

        response = self.guest_client.post(
            url_comment_add,
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response, f'/auth/login/?next={url_comment_add}')
        self.assertEqual(Comment.objects.count(), comment_count)


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
    fixtures = ('db.json',)

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
class PostsViewsImageTests(TestCase):
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
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsViewsImageTests.user)

    def test_posts_post_img_check_presence_context_index_page(self):
        """Проверяет наличие поста с картинкой на странице Index."""
        post = Post.objects.first()

        response = self.authorized_client.get(
            reverse(PostsViewsImageTests.post_index_endpoint))
        post_with_image = response.context['page_obj'][0].image.url

        self.assertEqual(post.image.url, post_with_image)

    def test_posts_post_img_check_presence_context_profile_page(self):
        """Проверяет наличие поста с картинкой на странице profile."""
        author = User.objects.get(username='auth')
        post = Post.objects.filter(author=author).first()

        response = self.authorized_client.get(
            reverse(PostsViewsImageTests.post_profile_endpoint,
                    kwargs={'username': author.username}))
        post_with_image = response.context['page_obj'][0].image.url

        self.assertEqual(post.image.url, post_with_image)

    def test_posts_post_img_check_presence_context_group_list_page(self):
        """Проверяет наличие поста с картинкой на странице group_list."""
        group = Group.objects.get(title='Тестовая группа c картинкой')
        post = Post.objects.filter(group=group).first()

        response = self.authorized_client.get(
            reverse(
                PostsViewsImageTests.post_group_list_endpoint,
                kwargs={'slug': group.slug}))
        post_with_image = response.context['page_obj'][0].image.url

        self.assertEqual(post.image.url, post_with_image)

    def test_posts_post_img_check_presence_context_post_detail_page(self):
        """Проверяет наличие поста с картинкой на странице post_detail"""
        post = Post.objects.get(group__title='Тестовая группа c картинкой')

        response = self.authorized_client.get(
            reverse(PostsViewsImageTests.post_detail_endpoint,
                    kwargs={'post_id': post.id}))
        context_post_detail = response.context['post_detail']

        self.assertEqual(post.image.url, context_post_detail.image.url)
