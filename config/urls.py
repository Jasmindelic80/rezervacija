"""
config/urls.py — Glavni URL konfigurator
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Glavne stranice
    path('', include('apps.businesses.urls')),

    # Autentifikacija
    path('', include('apps.accounts.urls')),

    # Termini
    path('termin/', include('apps.appointments.urls')),

    # Notifikacije — postavke
    path('profil/', include('apps.notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# ============================================================
# apps/accounts/urls.py
# ============================================================
"""
from django.urls import path
from . import views, login_views

urlpatterns = [
    path('registracija/',               views.register_step1_phone,   name='register'),
    path('registracija/verifikacija/',  views.register_step2_verify,  name='register_verify'),
    path('registracija/profil/',        views.register_step3_complete, name='register_complete'),
    path('registracija/resend/',        views.resend_otp,              name='resend_otp'),
    path('prijava/',                    login_views.login_with_phone,  name='login'),
    path('odjava/',                     login_views.logout_view,       name='logout'),
    path('profil/postavke/',            views.profile_settings,        name='profile_settings'),
]
"""

# ============================================================
# apps/businesses/urls.py
# ============================================================
"""
from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.home,              name='home'),
    path('pretraga/',                     views.search,            name='search'),
    path('kategorija/<slug:slug>/',       views.category_list,     name='category'),
    path('biznis/<slug:slug>/',           views.business_detail,   name='business_detail'),
    path('biznis/registracija/',          views.register_business, name='register_business'),
    path('biznis/<slug:slug>/uredi/',     views.edit_business,     name='edit_business'),
    path('dashboard/',                    views.provider_dashboard, name='provider_dashboard'),
    # AJAX
    path('api/slobodni-termini/',         views.available_slots_api, name='slots_api'),
]
"""

# ============================================================
# apps/appointments/urls.py
# ============================================================
"""
from django.urls import path
from . import views

urlpatterns = [
    path('novi/<slug:business_slug>/',  views.book_appointment,    name='book'),
    path('potvrda/<uuid:pk>/',          views.appointment_confirm, name='appointment_confirm'),
    path('otkazi/<uuid:pk>/',           views.cancel_appointment,  name='cancel'),
    path('moji-termini/',               views.my_appointments,     name='my_appointments'),
]
"""

# ============================================================
# apps/notifications/urls.py
# ============================================================
"""
from django.urls import path
from . import views

urlpatterns = [
    path('notifikacije/',  views.notification_settings, name='notification_settings'),
]
"""
