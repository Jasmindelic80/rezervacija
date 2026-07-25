from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

from .models import BlogPost, BlogCategory


def post_list(request):
    posts = BlogPost.objects.filter(is_published=True).select_related('category', 'author')

    category_slug = request.GET.get('kategorija', '')
    if category_slug:
        posts = posts.filter(category__slug=category_slug)

    paginator = Paginator(posts, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'categories': BlogCategory.objects.all(),
        'active_category': category_slug,
    }
    return render(request, 'blog/list.html', context)


def post_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    related_posts = BlogPost.objects.filter(
        is_published=True, category=post.category
    ).exclude(pk=post.pk)[:3]

    context = {
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'blog/detail.html', context)
