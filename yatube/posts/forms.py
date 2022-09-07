from django.forms import ModelForm
from django.forms import Textarea

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['text', 'group', 'image']
        labels = {
            'text': 'Текст поста',
            'group': 'Группы'
        }
        widgets = {
            'text': Textarea(attrs={'style': 'height: 193px;'}),
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
