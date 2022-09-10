from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from .utils import paginate_posts

POSTS_PER_PAGE = 10


def index(request):
    post_list = Post.objects.all()
    page_obj = paginate_posts(request, post_list, POSTS_PER_PAGE)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = paginate_posts(request, posts, POSTS_PER_PAGE)
    context = {
        'group': group,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    count_post = post_list.count()
    page_obj = paginate_posts(request, post_list, POSTS_PER_PAGE)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user, author=author).exists()
    else:
        following = None

    context = {
        'author': author,
        'page_obj': page_obj,
        'count': count_post,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    author = post.author
    count = author.posts.count()
    comments = post.comments.all()
    context = {
        'author': author,
        'post_detail': post,
        'count': count,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'

    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if request.method == 'POST':
        if form.is_valid():
            auth_user = request.user
            new_post = form.save(commit=False)
            new_post.author = auth_user
            new_post.save()
            return redirect('posts:profile', username=request.user.username)

    return render(request, template, {'form': form})


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id=post_id)

    context = {
        'is_edit': True,
        'form': form,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(
        author__following__user=request.user).select_related(
        'author', 'group')
    page_obj = paginate_posts(request, post_list, POSTS_PER_PAGE)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    current_user = request.user
    author = get_object_or_404(User, username=username)
    if author != current_user:
        Follow.objects.get_or_create(author=author, user=current_user)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    current_user = request.user
    author = get_object_or_404(User, username=username)
    follow_obj = Follow.objects.filter(author=author, user=current_user)
    follow_obj.delete()
    return redirect('posts:follow_index')
