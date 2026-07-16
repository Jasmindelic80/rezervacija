from django.shortcuts import redirect
from django.urls import resolve, reverse, Resolver404

EXEMPT_PREFIXES = (
    '/pretplata/',
    '/admin/',
    '/prijava/',
    '/odjava/',
    '/registracija/',
    '/static/',
    '/media/',
    '/i18n/',
    '/rosetta/',
    '/api/',
)

# Klijentske akcije (rezervacija termina, otkazivanje, itd.) — ne smiju biti
# blokirane istekom pretplate biznisa u kojem je vlasnik ujedno i klijent.
EXEMPT_URL_NAMES = (
    'book',
    'appointment_confirm',
    'appointment_ics',
    'cancel',
    'reschedule',
    'my_appointments',
    'home',
    'search',
    'category',
    'business_detail',
)

# Provider stranice koje se tiču upravljanja konkretnim biznisom — vežu se
# uz URL kwarg 'slug' koji identifikuje taj biznis.
BUSINESS_SLUG_KWARG = 'slug'


class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.is_staff
            and request.user.is_provider()
            and not any(request.path.startswith(p) for p in EXEMPT_PREFIXES)
        ):
            try:
                match = resolve(request.path)
            except Resolver404:
                match = None

            slug = match.kwargs.get(BUSINESS_SLUG_KWARG) if match else None

            # Bez slug-a u URL-u stranica se ne tiče upravljanja konkretnim
            # biznisom (npr. dashboard, postavke) — ne blokiramo je.
            if match and match.url_name not in EXEMPT_URL_NAMES and slug:
                business = request.user.businesses.select_related('subscription').filter(slug=slug).first()

                if business:
                    try:
                        sub = business.subscription
                        sub.sync_status()
                        if not sub.is_active:
                            return redirect(reverse('subscription_expired', kwargs={'slug': business.slug}))
                    except Exception:
                        pass

        return self.get_response(request)
