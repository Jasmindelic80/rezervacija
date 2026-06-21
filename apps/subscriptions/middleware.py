from django.shortcuts import redirect
from django.urls import reverse

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
            business = request.user.businesses.select_related('subscription').first()
            if business:
                try:
                    sub = business.subscription
                    sub.sync_status()
                    if not sub.is_active:
                        return redirect(reverse('subscription_expired'))
                except Exception:
                    pass

        return self.get_response(request)
