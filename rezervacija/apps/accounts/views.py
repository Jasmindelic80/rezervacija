from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from .models import PhoneOTP
from .forms import PhoneInputForm, OTPVerifyForm, CompleteProfileForm
from .sms import send_otp_sms

User = get_user_model()


@require_http_methods(['GET', 'POST'])
def register_step1_phone(request):
    """Korak 1: Unesi broj telefona → pošalji OTP"""
    if request.user.is_authenticated:
        return redirect('home')

    form = PhoneInputForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data['phone']
        role = form.cleaned_data['role']

        # Provjeri je li broj već registrovan
        if User.objects.filter(phone=phone).exists():
            existing = User.objects.get(phone=phone)
            if existing.phone_verified:
                messages.info(request, 'Ovaj broj je već registrovan. Prijavite se.')
                return redirect('login')

        # Generiši i pošalji OTP
        otp_obj = PhoneOTP.create_for_phone(phone, purpose='register')
        success = send_otp_sms(phone, otp_obj.otp, purpose='register')

        if not success:
            messages.error(request, 'Greška pri slanju SMS-a. Pokušajte ponovo.')
            return render(request, 'accounts/register_phone.html', {'form': form})

        request.session['reg_phone'] = phone
        request.session['reg_role'] = role

        messages.success(request, f'Kod poslan na {phone}')
        return redirect('register_verify')

    return render(request, 'accounts/register_phone.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def register_step2_verify(request):
    """Korak 2: Unesi OTP kod"""
    phone = request.session.get('reg_phone')
    if not phone:
        return redirect('register')

    form = OTPVerifyForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        otp_input = form.cleaned_data['otp']

        try:
            otp_obj = PhoneOTP.objects.filter(
                phone=phone, purpose='register', verified=False
            ).latest('created_at')
        except PhoneOTP.DoesNotExist:
            messages.error(request, 'Nema aktivnog koda. Zatražite novi.')
            return redirect('register')

        otp_obj.attempts += 1
        otp_obj.save()

        if otp_obj.is_expired():
            messages.error(request, 'Kod je istekao. Zatražite novi.')
            return redirect('register')

        if otp_obj.attempts > 5:
            messages.error(request, 'Previše pokušaja. Zatražite novi kod.')
            return redirect('register')

        if otp_obj.otp != otp_input:
            remaining = 5 - otp_obj.attempts
            messages.error(request, f'Pogrešan kod. Još {remaining} pokušaj(a).')
            return render(request, 'accounts/register_verify.html', {
                'form': form, 'phone': phone
            })

        otp_obj.verified = True
        otp_obj.save()
        request.session['reg_phone_verified'] = True
        return redirect('register_complete')

    return render(request, 'accounts/register_verify.html', {
        'form': form,
        'phone': phone
    })


@require_http_methods(['GET', 'POST'])
def register_step3_complete(request):
    """Korak 3: Dopuni profil i kreiraj nalog"""
    phone = request.session.get('reg_phone')
    verified = request.session.get('reg_phone_verified')
    role = request.session.get('reg_role', 'client')

    if not phone or not verified:
        return redirect('register')

    form = CompleteProfileForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data

        base_username = f"user_{phone.replace('+', '').replace(' ', '')}"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            password=cd['password'],
            first_name=cd['first_name'],
            last_name=cd['last_name'],
            email=cd.get('email', ''),
            phone=phone,
            phone_verified=True,
            role=role,
        )

        for key in ['reg_phone', 'reg_role', 'reg_phone_verified']:
            request.session.pop(key, None)

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Dobrodošli, {user.first_name}! Nalog je uspješno kreiran.')

        if role == 'provider':
            return redirect('register_business')
        return redirect('home')

    return render(request, 'accounts/register_complete.html', {'form': form, 'phone': phone})


@require_http_methods(['POST'])
def resend_otp(request):
    """Ponovo pošalji OTP"""
    phone = request.session.get('reg_phone')
    if not phone:
        return redirect('register')

    otp_obj = PhoneOTP.create_for_phone(phone, purpose='register')
    send_otp_sms(phone, otp_obj.otp, purpose='register')
    messages.info(request, 'Novi kod je poslan.')
    return redirect('register_verify')


@login_required
def profile_settings(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.city = request.POST.get('city', user.city)
        user.save()
        messages.success(request, 'Profil je uspješno ažuriran.')
        return redirect('profile_settings')

    return render(request, 'accounts/profile_settings.html', {'user': request.user})