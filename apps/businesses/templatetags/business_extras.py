from django import template
from django.utils.translation import gettext

register = template.Library()


@register.filter
def translate(value):
    """Prevede tekst iz baze (npr. naziv kategorije) preko gettext kataloga."""
    if not value:
        return value
    return gettext(value)
