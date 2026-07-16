from django.urls import path
from . import views

urlpatterns = [
    path('', views.subscription_dashboard, name='subscription_dashboard'),
    path('<slug:slug>/', views.subscription_dashboard, name='subscription_dashboard'),
    path('placanje/', views.payment_choose, name='payment_choose'),
    path('placanje/<slug:slug>/', views.payment_choose, name='payment_choose'),
    path('placanje/banka/', views.payment_bank_initiate, name='payment_bank_initiate'),
    path('placanje/banka/<slug:slug>/', views.payment_bank_initiate, name='payment_bank_initiate'),
    path('placanje/banka/<int:payment_id>/dokaz/', views.payment_bank_upload, name='payment_bank_upload'),
    path('placanje/paypal/', views.payment_paypal_create, name='payment_paypal_create'),
    path('placanje/paypal/<slug:slug>/', views.payment_paypal_create, name='payment_paypal_create'),
    path('placanje/paypal/<int:payment_id>/potvrda/', views.payment_paypal_capture, name='payment_paypal_capture'),
    path('istekla/', views.subscription_expired, name='subscription_expired'),
    path('istekla/<slug:slug>/', views.subscription_expired, name='subscription_expired'),
]
