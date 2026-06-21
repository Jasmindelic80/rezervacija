from django.utils import translation


class DefaultLanguageMiddleware:
    """Force Bosnian as default unless user explicitly chose a language via the switcher."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_picked = (
            '_language' in request.session
            or 'django_language' in request.COOKIES
        )
        if not user_picked:
            translation.activate('bs')
            request.LANGUAGE_CODE = 'bs'
        return self.get_response(request)
