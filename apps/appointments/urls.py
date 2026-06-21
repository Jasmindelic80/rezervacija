from django.urls import path
from . import views
from . import provider_views

urlpatterns = [
    # Klijentski URLs
    path('novi/<slug:business_slug>/', views.book_appointment, name='book'),
    path('potvrda/<uuid:pk>/', views.appointment_confirm, name='appointment_confirm'),
    path('otkazi/<uuid:pk>/', views.cancel_appointment, name='cancel'),
    path('moji-termini/', views.my_appointments, name='my_appointments'),

    # Provider portal
    path('dashboard/', provider_views.provider_dashboard, name='provider_dashboard'),
    path('termini/<slug:slug>/', provider_views.provider_appointments, name='provider_appointments'),
    path('termin/<uuid:pk>/', provider_views.provider_appointment_detail, name='provider_appointment_detail'),
    path('termin/<uuid:pk>/akcija/', provider_views.provider_appointment_action, name='provider_appointment_action'),
    path('termin-novi/<slug:slug>/', provider_views.provider_appointment_create, name='provider_appointment_create'),
    path('radno-vrijeme/<slug:slug>/', provider_views.provider_working_hours, name='provider_working_hours'),
    path('blokade/<slug:slug>/', provider_views.provider_blocked_slots, name='provider_blocked_slots'),
    path('blokada/<int:pk>/obrisi/', provider_views.provider_blocked_slot_delete, name='provider_blocked_slot_delete'),
    path('kalendar/<slug:slug>/', provider_views.provider_calendar, name='provider_calendar'),
    path('kalendar/<slug:slug>/dan/', provider_views.provider_calendar_day, name='provider_calendar_day'),
]
