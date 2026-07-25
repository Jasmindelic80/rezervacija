from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap, index
from django.views.generic import TemplateView
from apps.businesses.sitemaps import (
    StaticViewSitemap,
    BusinessSitemap,
    CategorySitemap,
)
from apps.blog.sitemaps import BlogPostSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'businesses': BusinessSitemap,
    'categories': CategorySitemap,
    'blog': BlogPostSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('apps.businesses.urls')),
    path('', include('apps.accounts.urls')),
    path('termin/', include('apps.appointments.urls')),
    path('profil/', include('apps.notifications.urls')),
    path('pretplata/', include('apps.subscriptions.urls')),
    path('blog/', include('apps.blog.urls')),
    path('i18n/', include('django.conf.urls.i18n')),

    path('impressum/', TemplateView.as_view(template_name='legal/impressum.html'), name='impressum'),
    path('privatnost/', TemplateView.as_view(template_name='legal/privacy.html'), name='privacy'),

    path('sitemap.xml', index, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.index'),
    path('sitemap-<section>.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),

    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain'
    )),
]

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [path('rosetta/', include('rosetta.urls'))]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
