from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    register_step1_phone,
    register_step2_verify,
    register_step3_complete,
    resend_otp,
    profile_settings,
    register_simple,
)
from .login_views import login_with_phone

urlpatterns = [
    path('registracija/',               register_simple,         name='register'),
    path('registracija/sms/',           register_step1_phone,    name='register_sms'),
    path('registracija/verifikacija/',  register_step2_verify,   name='register_verify'),
    path('registracija/profil/',        register_step3_complete, name='register_complete'),
    path('registracija/resend/',        resend_otp,              name='resend_otp'),
    path('prijava/',                    login_with_phone,        name='login'),
    path('odjava/',                     LogoutView.as_view(),    name='logout'),
    path('profil/postavke/',            profile_settings,        name='profile_settings'),
]
