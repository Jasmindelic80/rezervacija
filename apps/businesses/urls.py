from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('pretraga/', views.search, name='search'),
    path('kategorija/<slug:slug>/', views.category, name='category'),
    path('biznis/<slug:slug>/', views.business_detail, name='business_detail'),
    path('biznis/registracija/', views.register_business, name='register_business'),
    path('api/slobodni-termini/', views.available_slots_api, name='slots_api'),
]