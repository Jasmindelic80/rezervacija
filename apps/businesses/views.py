from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import date, datetime, timedelta
import math
import json

from .models import Business, Category
from apps.services.models import Service
from apps.availability.utils import get_available_slots, get_next_available_date
from .city_coords import CITY_COORDS, fold_city_name, lookup_city_coords as _lookup_city_coords

_fold_city_name = fold_city_name


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlng = math.radians(float(lng2) - float(lng1))
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _filter_by_location(businesses, lat, lng, radius_km):
    result = []
    for biz in businesses:
        if biz.latitude is None or biz.longitude is None:
            continue
        dist = _haversine_km(lat, lng, biz.latitude, biz.longitude)
        if dist <= radius_km:
            biz.distance_km = round(dist, 1)
            result.append(biz)
    return result


def _annotate_next_slot(businesses):
    """Doda _next_date i _next_slot na svaki Business objekt i sortira po njima."""
    for biz in businesses:
        svc = next((s for s in biz.services.all() if s.is_active), None)
        if svc:
            biz.next_date, biz.next_slot = get_next_available_date(biz, svc, days_ahead=14)
        else:
            biz.next_date = biz.next_slot = None

    businesses.sort(key=lambda b: (
        0 if b.next_date else 1,
        b.next_date or date.max,
        b.next_slot.time() if b.next_slot else datetime.max.time(),
    ))
    return businesses


def home(request):
    categories = Category.objects.annotate(
        business_count=Count('businesses', filter=Q(businesses__is_active=True))
    ).filter(business_count__gt=0).order_by('order')

    featured = Business.objects.filter(
        is_active=True, is_verified=True
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-avg_rating')[:6]

    from apps.appointments.models import Appointment

    context = {
        'categories': categories,
        'featured_businesses': featured,
        'cities': Business.objects.filter(is_active=True)
        .values_list('city', flat=True).distinct().order_by('city'),
        'stats_businesses': Business.objects.filter(is_active=True).count(),
        'stats_categories': categories.count(),
        'stats_appointments': Appointment.objects.count(),
    }
    return render(request, 'home.html', context)


def search(request):
    qs = Business.objects.filter(is_active=True).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).prefetch_related('services')

    category_slug = request.GET.get('kategorija', '')
    city = request.GET.get('grad', '')
    query = request.GET.get('q', '')
    user_lat = request.GET.get('lat', '')
    user_lng = request.GET.get('lng', '')
    radius = request.GET.get('radius', '10')

    using_location = bool(user_lat and user_lng)

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(services__name__icontains=query)
        ).distinct()

    businesses = list(qs)

    if using_location:
        try:
            radius_km = int(radius)
            businesses = _filter_by_location(businesses, float(user_lat), float(user_lng), radius_km)
        except (ValueError, TypeError):
            using_location = False
    elif city:
        businesses = [b for b in businesses if _fold_city_name(b.city) == _fold_city_name(city)]

    location_mode = 'gps' if using_location else ('city' if city else 'exact')

    businesses = _annotate_next_slot(businesses)

    today = date.today()
    context = {
        'businesses': businesses,
        'categories': Category.objects.all(),
        'selected_category': category_slug,
        'selected_city': city,
        'query': query,
        'today': today,
        'tomorrow': today + timedelta(days=1),
        'using_location': using_location,
        'location_mode': location_mode,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'radius': radius,
        'cities': Business.objects.filter(is_active=True)
            .values_list('city', flat=True).distinct().order_by('city'),
    }
    return render(request, 'search/results.html', context)


def business_detail(request, slug):
    business = get_object_or_404(Business, slug=slug, is_active=True)
    services = business.services.filter(is_active=True)
    staff = business.staff.filter(is_active=True)
    reviews = business.reviews.filter(is_approved=True).select_related('client')[:10]

    # Provjeri sljedeći slobodan termin za prvu uslugu
    first_service = services.first()
    next_date = next_slot = None
    if first_service:
        next_date, next_slot = get_next_available_date(business, first_service)

    context = {
        'business': business,
        'services': services,
        'staff': staff,
        'reviews': reviews,
        'next_available_date': next_date,
        'next_available_slot': next_slot,
        'today': date.today(),
    }
    return render(request, 'businesses/detail.html', context)


def available_slots_api(request):
    """AJAX endpoint za dohvat slobodnih termina"""
    business_id = request.GET.get('business_id')
    service_id = request.GET.get('service_id')
    staff_id = request.GET.get('staff_id')
    date_str = request.GET.get('date')

    if not all([business_id, service_id, date_str]):
        return JsonResponse({'error': 'Nedostaju parametri'}, status=400)

    try:
        target_date = date.fromisoformat(date_str)
        business = Business.objects.get(id=business_id, is_active=True)
        service = Service.objects.get(id=service_id, business=business)

        staff = None
        if staff_id and staff_id != 'any':
            from apps.businesses.models import Staff
            staff = Staff.objects.get(id=staff_id, business=business)

        slots = get_available_slots(business, service, staff, target_date)

        return JsonResponse({
            'slots': [s.strftime('%H:%M') for s in slots],
            'date': date_str,
            'count': len(slots),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def category(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    city = request.GET.get('grad', '')
    user_lat = request.GET.get('lat', '')
    user_lng = request.GET.get('lng', '')
    radius = request.GET.get('radius', '10')
    using_location = bool(user_lat and user_lng)

    qs = Business.objects.filter(
        is_active=True, category=cat
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).prefetch_related('services')

    businesses = list(qs)

    if using_location:
        try:
            radius_km = int(radius)
            businesses = _filter_by_location(businesses, float(user_lat), float(user_lng), radius_km)
        except (ValueError, TypeError):
            using_location = False
    elif city:
        businesses = [b for b in businesses if _fold_city_name(b.city) == _fold_city_name(city)]

    location_mode = 'gps' if using_location else ('city' if city else 'exact')

    businesses = _annotate_next_slot(businesses)

    today = date.today()
    context = {
        'category': cat,
        'businesses': businesses,
        'categories': Category.objects.all(),
        'selected_city': city,
        'today': today,
        'tomorrow': today + timedelta(days=1),
        'using_location': using_location,
        'location_mode': location_mode,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'radius': radius,
        'cities': Business.objects.filter(is_active=True)
            .values_list('city', flat=True).distinct().order_by('city'),
    }
    return render(request, 'search/results.html', context)


def cities_api(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'cities': []})

    biz_cities = set(
        Business.objects
        .filter(is_active=True, city__istartswith=q)
        .values_list('city', flat=True)
        .distinct()
    )

    all_names = sorted({
        name for name in list(biz_cities) + list(CITY_COORDS.keys())
        if name.lower().startswith(q.lower())
    })[:8]

    result = []
    for name in all_names:
        coords = CITY_COORDS.get(name)
        result.append({
            'name': name,
            'lat': coords[0] if coords else None,
            'lng': coords[1] if coords else None,
        })
    return JsonResponse({'cities': result})

@login_required
def register_business(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        category_id = request.POST.get('category', '')
        city = request.POST.get('city', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        registration_number = request.POST.get('registration_number', '').strip()

        if name and city and phone and registration_number:
            if not (registration_number.isdigit() and len(registration_number) == 13):
                messages.error(request, 'JIB/ID broj firme mora sadržavati tačno 13 brojeva.')
            elif Business.objects.filter(registration_number=registration_number).exists():
                messages.error(
                    request,
                    'Firma sa ovim JIB/ID brojem je već registrovana na BookBiH. '
                    'Besplatni probni period se može iskoristiti samo jednom po firmi.'
                )
            else:
                category = Category.objects.filter(id=category_id).first()
                coords = _lookup_city_coords(city)
                business = Business.objects.create(
                    owner=request.user,
                    category=category,
                    name=name,
                    city=city,
                    phone=phone,
                    address=address,
                    registration_number=registration_number,
                    latitude=coords[0],
                    longitude=coords[1],
                )
                # Postavi korisnika kao providera
                request.user.role = 'provider'
                request.user.save()

                messages.success(request, f'Biznis "{business.name}" je uspješno registrovan!')
                return redirect('provider_dashboard')
        else:
            messages.error(request, 'Molimo popunite sva obavezna polja.')

    categories = Category.objects.all().order_by('order')
    has_business = request.user.businesses.exists()
    return render(request, 'businesses/register.html', {
        'categories': categories, 'has_business': has_business,
    })


@login_required
def edit_business(request, slug):
    business = get_object_or_404(Business, slug=slug, owner=request.user)
    categories = Category.objects.all().order_by('order')

    if request.method == 'POST':
        old_city = business.city
        business.name = request.POST.get('name', business.name).strip()
        business.description = request.POST.get('description', '')
        business.address = request.POST.get('address', business.address).strip()
        business.city = request.POST.get('city', business.city).strip()
        business.canton = request.POST.get('canton', '')
        business.phone = request.POST.get('phone', business.phone).strip()
        business.email = request.POST.get('email', '')
        business.website = request.POST.get('website', '')
        business.instagram = request.POST.get('instagram', '')
        interval = request.POST.get('appointment_interval_minutes', '')
        if interval.isdigit():
            business.appointment_interval_minutes = int(interval)
        cat_id = request.POST.get('category', '')
        business.category = Category.objects.filter(id=cat_id).first() if cat_id else None
        if request.FILES.get('logo'):
            business.logo = request.FILES['logo']
        if request.FILES.get('cover_image'):
            business.cover_image = request.FILES['cover_image']

        if business.name and business.city and business.phone and business.address:
            if business.city != old_city or business.latitude is None or business.longitude is None:
                coords = _lookup_city_coords(business.city)
                business.latitude, business.longitude = coords[0], coords[1]
            business.save()
            messages.success(request, 'Izmjene su sačuvane.')
            return redirect('edit_business', slug=business.slug)
        else:
            messages.error(request, 'Naziv, grad, telefon i adresa su obavezni.')

    from apps.businesses.models import Business as B
    ctx = {
        'business': business,
        'categories': categories,
        'active_business': business,
        'businesses': B.objects.filter(owner=request.user, is_active=True),
    }
    return render(request, 'businesses/edit.html', ctx)


