from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Business, Category


class StaticViewSitemap(Sitemap):
    protocol = 'https'
    priority = 1.0
    changefreq = 'weekly'

    def items(self):
        return [
            'home',
            'search',
            'register',
            'login',
            'register_business',
        ]

    def location(self, item):
        return reverse(item)


class BusinessSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Business.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('business_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('category', kwargs={'slug': obj.slug})
