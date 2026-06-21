from django.urls import path
from . import views
from apps.services import views as service_views

urlpatterns = [
    path('', views.home, name='home'),
    path('pretraga/', views.search, name='search'),
    path('kategorija/<slug:slug>/', views.category, name='category'),
    path('biznis/registracija/', views.register_business, name='register_business'),
    path('biznis/<slug:slug>/uredi/', views.edit_business, name='edit_business'),
    path('biznis/<slug:slug>/usluge/', service_views.manage_services, name='manage_services'),
    path('biznis/<slug:slug>/usluge/dodaj/', service_views.add_service, name='add_service'),
    path('biznis/<slug:slug>/usluge/<int:service_id>/obrisi/', service_views.delete_service, name='delete_service'),
    path('biznis/<slug:slug>/usluge/<int:service_id>/toggle/', service_views.toggle_service, name='toggle_service'),
    path('biznis/<slug:slug>/', views.business_detail, name='business_detail'),
    path('api/slobodni-termini/', views.available_slots_api, name='slots_api'),
    path('api/gradovi/', views.cities_api, name='cities_api'),
]