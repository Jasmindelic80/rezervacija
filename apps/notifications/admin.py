from django.contrib import admin
from .models import NotificationPreference, NotificationLog

admin.site.register(NotificationPreference)
admin.site.register(NotificationLog)