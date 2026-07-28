from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='blog_list'),
    path('<slug:slug>/', views.post_detail, name='blog_detail'),
]
