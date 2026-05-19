from django.urls import path
from . import views
from .provider_views import provider_dashboard

urlpatterns = [
    path('novi/<slug:business_slug>/', views.book_appointment, name='book'),
    path('potvrda/<uuid:pk>/', views.appointment_confirm, name='appointment_confirm'),
    path('otkazi/<uuid:pk>/', views.cancel_appointment, name='cancel'),
    path('moji-termini/', views.my_appointments, name='my_appointments'),
    path('dashboard/', provider_dashboard, name='provider_dashboard'),
]