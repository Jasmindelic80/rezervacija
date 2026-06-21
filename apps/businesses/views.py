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

CITY_COORDS = {
    'Sarajevo': (43.8563, 18.4131),
    'Banja Luka': (44.7722, 17.1910),
    'Tuzla': (44.5384, 18.6736),
    'Zenica': (44.2019, 17.9078),
    'Mostar': (43.3438, 17.8078),
    'Bijeljina': (44.7578, 19.2144),
    'Brčko': (44.8694, 18.8097),
    'Prijedor': (44.9799, 16.7147),
    'Trebinje': (42.7113, 18.3441),
    'Travnik': (44.2264, 17.6633),
    'Cazin': (45.2211, 15.9431),
    'Bihać': (44.8175, 15.8706),
    'Visoko': (43.9897, 18.1764),
    'Konjic': (43.6514, 17.9613),
    'Livno': (43.8250, 17.0094),
    'Doboj': (44.7317, 18.0856),
    'Goražde': (43.6667, 18.9778),
    'Foča': (43.5072, 18.7758),
    'Zvornik': (44.3869, 19.1025),
    'Gradiška': (45.1494, 17.2531),
    'Lukavac': (44.5394, 18.5267),
    'Kakanj': (44.1272, 18.1025),
    'Vitez': (44.1572, 17.7894),
    'Hadžići': (43.8233, 18.2022),
    'Ilijaš': (43.9575, 18.2706),
    'Vogošća': (43.9000, 18.3378),
    'Ilidža': (43.8300, 18.3100),
    'Pale': (43.8181, 18.5683),
    'Tešanj': (44.6128, 17.9872),
    'Gradačac': (44.8794, 18.4269),
    'Gračanica': (44.7008, 18.3053),
    'Žepče': (44.4258, 18.0400),
    'Zavidovići': (44.4431, 18.1497),
    'Maglaj': (44.5500, 18.0969),
    'Jajce': (44.3414, 17.2703),
    'Bugojno': (44.0564, 17.4503),
    'Fojnica': (43.9681, 17.9025),
    'Breza': (43.9992, 18.2639),
    'Vareš': (44.1650, 18.3289),
    'Olovo': (44.1258, 18.6467),
    'Kladanj': (44.2278, 18.6928),
    'Kotor Varoš': (44.6194, 17.3731),
    'Laktaši': (44.9000, 17.2986),
    'Šipovo': (44.2764, 17.0900),
    'Glamoč': (43.9686, 16.8494),
    'Drvar': (44.3731, 16.3806),
    'Sanski Most': (44.7681, 16.6694),
    'Ključ': (44.5339, 16.7719),
    'Bosanska Krupa': (44.8833, 16.1500),
    'Bosanski Petrovac': (44.5497, 16.3703),
    'Čapljina': (43.1108, 17.6942),
    'Ljubuški': (43.1978, 17.5506),
    'Široki Brijeg': (43.3836, 17.5964),
    'Grude': (43.3697, 17.4333),
    'Posušje': (43.4689, 17.3261),
    'Tomislavgrad': (43.7158, 17.2294),
    'Neum': (42.9253, 17.6147),
    'Stolac': (43.0847, 17.9556),
    'Berkovići': (43.1544, 18.3250),
    'Gacko': (43.1669, 18.5358),
    'Nevesinje': (43.2578, 18.1136),
    'Kalinovik': (43.5097, 18.4361),
    'Rogatica': (43.8003, 19.0025),
    'Sokolac': (43.9356, 18.7975),
    'Han Pijesak': (44.0736, 18.9689),
    'Vlasenica': (44.1822, 18.9528),
    'Milići': (44.1719, 19.0989),
    'Srebrenica': (44.1039, 19.2978),
    'Bratunac': (44.1844, 19.3308),
    'Ljubovija': (44.1897, 19.3750),
    'Šekovići': (44.2992, 18.8514),
    'Lopare': (44.6383, 18.8478),
    'Ugljevik': (44.6900, 18.9617),
    'Šamac': (45.0581, 18.4628),
    'Odžak': (45.0072, 18.3244),
    'Modriča': (44.9553, 18.2989),
    'Derventa': (44.9744, 17.9097),
    'Prnjavor': (44.8694, 17.6608),
    'Srbac': (45.0964, 17.5275),
    'Brod': (45.1294, 17.9875),
    'Kostajnica': (45.2222, 16.5456),
    'Novi Grad': (45.0533, 16.3758),
    'Krupa na Uni': (44.8931, 16.2875),
    'Mrkonjić Grad': (44.4133, 17.0814),
    'Kneževo': (44.4933, 17.3744),
    'Čelinac': (44.7253, 17.3208),
    'Srbobran': (44.5436, 17.8158),
    'Pećigrad': (45.1967, 15.8817),
    'Bosanska Dubica': (45.1728, 16.8083),
    'Bosanski Brod': (45.1294, 17.9875),
}


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

    context = {
        'categories': categories,
        'featured_businesses': featured,
        'cities': Business.objects.filter(is_active=True)
        .values_list('city', flat=True).distinct().order_by('city'),
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
        businesses = [b for b in businesses if b.city.lower() == city.lower()]

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
        businesses = [b for b in businesses if b.city.lower() == city.lower()]

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

        if name and city and phone:
            category = Category.objects.filter(id=category_id).first()
            coords = CITY_COORDS.get(city, (None, None))
            business = Business.objects.create(
                owner=request.user,
                category=category,
                name=name,
                city=city,
                phone=phone,
                address=address,
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
    return render(request, 'businesses/register.html', {'categories': categories})


@login_required
def edit_business(request, slug):
    business = get_object_or_404(Business, slug=slug, owner=request.user)
    categories = Category.objects.all().order_by('order')

    if request.method == 'POST':
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
            if business.latitude is None or business.longitude is None:
                coords = CITY_COORDS.get(business.city, (None, None))
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


