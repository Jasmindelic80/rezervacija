from django.urls import path
from . import views

urlpatterns = [
    path('notifikacije/', views.notification_settings, name='notification_settings'),
]