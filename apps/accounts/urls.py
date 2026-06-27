from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    register_step1_phone,
    register_step2_verify,
    register_step3_complete,
    resend_otp,
    profile_settings,
    register_simple,
    password_reset_request,
    password_reset_verify,
    password_reset_resend,
    password_reset_confirm,
)
from .login_views import login_with_phone

urlpatterns = [
    path('registracija/',               register_step1_phone,    name='register'),
    path('registracija/bez-sms/',       register_simple,         name='register_simple'),
    path('registracija/verifikacija/',  register_step2_verify,   name='register_verify'),
    path('registracija/profil/',        register_step3_complete, name='register_complete'),
    path('registracija/resend/',        resend_otp,              name='resend_otp'),
    path('prijava/',                    login_with_phone,        name='login'),
    path('odjava/',                     LogoutView.as_view(),    name='logout'),
    path('profil/postavke/',            profile_settings,        name='profile_settings'),
    path('reset-lozinke/',             password_reset_request,  name='password_reset_request'),
    path('reset-lozinke/kod/',         password_reset_verify,   name='password_reset_verify'),
    path('reset-lozinke/resend/',      password_reset_resend,   name='password_reset_resend'),
    path('reset-lozinke/nova/',        password_reset_confirm,  name='password_reset_confirm'),
]
