from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.businesses.models import Business
from .models import Service


def _services_context(request, business):
    from apps.businesses.models import Business as B
    return {
        'business': business,
        'active_business': business,
        'businesses': B.objects.filter(owner=request.user, is_active=True),
        'services': business.services.all(),
    }


@login_required
def manage_services(request, slug):
    business = get_object_or_404(Business, slug=slug, owner=request.user)
    return render(request, 'provider/services.html', _services_context(request, business))


@login_required
def add_service(request, slug):
    business = get_object_or_404(Business, slug=slug, owner=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        duration = request.POST.get('duration_minutes', '').strip()
        price = request.POST.get('price', '').strip()
        price_note = request.POST.get('price_note', '').strip()
        description = request.POST.get('description', '').strip()

        if name and duration and duration.isdigit() and price:
            try:
                Service.objects.create(
                    business=business,
                    name=name,
                    duration_minutes=int(duration),
                    price=price,
                    price_note=price_note,
                    description=description,
                )
                messages.success(request, f'Usluga "{name}" je dodana.')
            except Exception as e:
                messages.error(request, f'Greška: {e}')
        else:
            messages.error(request, 'Naziv, trajanje i cijena su obavezni.')

    return redirect('manage_services', slug=slug)


@login_required
def delete_service(request, slug, service_id):
    business = get_object_or_404(Business, slug=slug, owner=request.user)
    service = get_object_or_404(Service, id=service_id, business=business)

    if request.method == 'POST':
        name = service.name
        service.delete()
        messages.success(request, f'Usluga "{name}" je obrisana.')

    return redirect('manage_services', slug=slug)


@login_required
def toggle_service(request, slug, service_id):
    business = get_object_or_404(Business, slug=slug, owner=request.user)
    service = get_object_or_404(Service, id=service_id, business=business)

    if request.method == 'POST':
        service.is_active = not service.is_active
        service.save()

    return redirect('manage_services', slug=slug)
