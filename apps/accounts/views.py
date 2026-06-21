from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from .models import PhoneOTP
from .forms import EmailPhoneForm, OTPVerifyForm, CompleteProfileForm, COUNTRY_CODES
from .otp_sender import send_otp_email

User = get_user_model()


@require_http_methods(['GET', 'POST'])
def register_step1_phone(request):
    """Korak 1: Unesi email (+ opciono telefon) → pošalji OTP na email"""
    if request.user.is_authenticated:
        return redirect('home')

    form = EmailPhoneForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        phone = form.cleaned_data.get('phone')
        role = form.cleaned_data['role']

        if User.objects.filter(email=email).exists():
            messages.info(request, 'Ovaj email je već registrovan. Prijavite se.')
            return redirect('login')

        otp_obj = PhoneOTP.create_for_phone(email, purpose='register')
        success = send_otp_email(email, otp_obj.otp, purpose='register')

        if not success:
            messages.error(request, 'Greška pri slanju koda na email. Pokušajte ponovo.')
            return render(request, 'accounts/register_phone.html', {
                'form': form,
                'country_codes': COUNTRY_CODES,
            })

        request.session['reg_email'] = email
        request.session['reg_phone'] = phone
        request.session['reg_role'] = role

        messages.success(request, f'Kod je poslan na {email}')
        return redirect('register_verify')

    return render(request, 'accounts/register_phone.html', {
        'form': form,
        'country_codes': COUNTRY_CODES,
    })


@require_http_methods(['GET', 'POST'])
def register_step2_verify(request):
    """Korak 2: Unesi OTP kod poslan na email"""
    email = request.session.get('reg_email')
    if not email:
        return redirect('register')

    form = OTPVerifyForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        otp_input = form.cleaned_data['otp']

        try:
            otp_obj = PhoneOTP.objects.filter(
                phone=email, purpose='register', verified=False
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
                'form': form, 'email': email,
            })

        otp_obj.verified = True
        otp_obj.save()
        request.session['reg_phone_verified'] = True
        return redirect('register_complete')

    return render(request, 'accounts/register_verify.html', {
        'form': form,
        'email': email,
    })

@require_http_methods(['GET', 'POST'])
def register_simple(request):
    """Jednostavna registracija bez SMS verifikacije"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', 'client')

        # Validacija
        if not username or not password:
            messages.error(request, 'Username i lozinka su obavezni.')
            return render(request, 'accounts/register_simple.html')

        if password != password2:
            messages.error(request, 'Lozinke se ne podudaraju.')
            return render(request, 'accounts/register_simple.html')

        if len(password) < 8:
            messages.error(request, 'Lozinka mora imati najmanje 8 karaktera.')
            return render(request, 'accounts/register_simple.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ovaj username je već zauzet.')
            return render(request, 'accounts/register_simple.html')

        # Normalizuj telefon ako je unesen
        normalized_phone = None
        if phone:
            try:
                normalized_phone = normalize_phone(phone)
                if User.objects.filter(phone=normalized_phone).exists():
                    messages.error(request, 'Ovaj broj telefona je već registrovan.')
                    return render(request, 'accounts/register_simple.html')
            except Exception:
                normalized_phone = phone

        # Kreiraj korisnika
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=normalized_phone,
            phone_verified=True if normalized_phone else False,
            role=role,
        )

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Dobrodošli, {first_name or username}!')

        if role == 'provider':
            return redirect('register_business')
        return redirect('home')

    return render(request, 'accounts/register_simple.html')

@require_http_methods(['GET', 'POST'])
def register_step3_complete(request):
    """Korak 3: Dopuni profil i kreiraj nalog"""
    email = request.session.get('reg_email')
    verified = request.session.get('reg_phone_verified')
    role = request.session.get('reg_role', 'client')
    phone = request.session.get('reg_phone')

    if not email or not verified:
        return redirect('register')

    form = CompleteProfileForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data

        base_username = email.split('@')[0]
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
            email=email,
            phone=phone or None,
            phone_verified=bool(phone),
            role=role,
        )

        for key in ['reg_email', 'reg_phone', 'reg_role', 'reg_phone_verified']:
            request.session.pop(key, None)

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Dobrodošli, {user.first_name}! Nalog je uspješno kreiran.')

        if role == 'provider':
            return redirect('register_business')
        return redirect('home')

    return render(request, 'accounts/register_complete.html', {'form': form, 'email': email})


@require_http_methods(['POST'])
def resend_otp(request):
    """Ponovo pošalji OTP na email"""
    email = request.session.get('reg_email')
    if not email:
        return redirect('register')

    otp_obj = PhoneOTP.create_for_phone(email, purpose='register')
    send_otp_email(email, otp_obj.otp, purpose='register')
    messages.info(request, f'Novi kod je poslan na {email}.')
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