from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from .forms import normalize_phone

User = get_user_model()


@require_http_methods(['GET', 'POST'])
def login_with_phone(request):
    """Prijava: broj telefona + lozinka"""
    from django.contrib.auth import authenticate

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        phone_raw = request.POST.get('phone', '')
        password = request.POST.get('password', '')
        phone = normalize_phone(phone_raw)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            messages.error(request, 'Broj telefona nije registrovan.')
            return render(request, 'accounts/login.html', {'phone': phone_raw})

        if not user.phone_verified:
            messages.warning(request, 'Broj nije verificiran. Registrujte se ponovo.')
            return redirect('register')

        auth_user = authenticate(request, username=user.username, password=password)
        if auth_user:
            login(request, auth_user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Pogrešna lozinka.')

    return render(request, 'accounts/login.html')