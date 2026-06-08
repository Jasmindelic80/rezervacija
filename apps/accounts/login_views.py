from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from .forms import normalize_phone

User = get_user_model()


@require_http_methods(['GET', 'POST'])
def login_with_phone(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        identifier = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')

        # Pokušaj login s username direktno
        user = authenticate(request, username=identifier, password=password)

        # Ako ne radi, pokušaj naći usera po broju telefona
        if not user:
            try:
                phone = normalize_phone(identifier)
                db_user = User.objects.get(phone=phone)
                user = authenticate(request, username=db_user.username, password=password)
            except Exception:
                pass

        # Pokušaj i direktno po username
        if not user:
            try:
                db_user = User.objects.get(username=identifier)
                user = authenticate(request, username=identifier, password=password)
            except Exception:
                pass

        if user:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Pogrešan broj telefona/username ili lozinka.')

    return render(request, 'accounts/login.html')