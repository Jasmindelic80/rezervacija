from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, Count
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import date, timedelta
import json

from .models import Business, Category
from apps.services.models import Service
from apps.availability.utils import get_available_slots, get_next_available_date


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
    )

    category_slug = request.GET.get('kategorija', '')
    city = request.GET.get('grad', '')
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'rating')

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if city:
        qs = qs.filter(city__iexact=city)
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(services__name__icontains=query)
        ).distinct()

    if sort == 'rating':
        qs = qs.order_by('-avg_rating')
    elif sort == 'reviews':
        qs = qs.order_by('-review_count')
    elif sort == 'newest':
        qs = qs.order_by('-created_at')

    context = {
        'businesses': qs,
        'categories': Category.objects.all(),
        'selected_category': category_slug,
        'selected_city': city,
        'query': query,
        'sort': sort,
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
    qs = Business.objects.filter(
        is_active=True, category=cat
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-avg_rating')

    context = {
        'category': cat,
        'businesses': qs,
        'categories': Category.objects.all(),
        'cities': Business.objects.filter(is_active=True)
            .values_list('city', flat=True).distinct().order_by('city'),
    }
    return render(request, 'search/results.html', context)

@login_required
def register_business(request):
    if request.method == 'POST':
        # Osnovna registracija biznisa
        from .models import Category
        name = request.POST.get('name', '')
        category_id = request.POST.get('category', '')
        city = request.POST.get('city', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')

        if name and city and phone:
            category = Category.objects.filter(id=category_id).first()
            business = Business.objects.create(
                owner=request.user,
                category=category,
                name=name,
                city=city,
                phone=phone,
                address=address,
            )
            # Postavi korisnika kao providera
            request.user.role = 'provider'
            request.user.save()

            messages.success(request, f'Biznis "{business.name}" je uspješno registrovan!')
            return redirect('business_detail', slug=business.slug)
        else:
            messages.error(request, 'Molimo popunite sva obavezna polja.')

    categories = Category.objects.all().order_by('order')
    return render(request, 'businesses/register.html', {'categories': categories})