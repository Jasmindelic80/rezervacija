from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import BlogPost


class BlogPostSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return BlogPost.objects.filter(is_published=True)

    def location(self, obj):
        return reverse('blog_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at
