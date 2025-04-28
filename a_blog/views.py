from django.shortcuts import render
from operator import attrgetter
from .models import ArticlePage, BlogCategory


def article_search(request):
    search_query = request.GET.get('query', '').strip()
    category_slug = request.GET.get('category', '')
    tag = request.GET.get('tag', '')

    articles = ArticlePage.objects.live().specific()

    if search_query:
        articles = articles.search(search_query)

    if category_slug:
        articles = articles.filter(category__slug=category_slug)

    if tag:
        articles = articles.filter(tags__name=tag)

    articles = sorted(articles, key=attrgetter('first_published_at'), reverse=True)

    categories = BlogCategory.objects.all()

    context = {
        'articles': articles,
        'search_query': search_query,
        'categories': categories,
        'current_category': category_slug,
        'tag': tag,
    }
    return render(request, 'a_blog/blog_page.html', context)