from django.contrib import admin
from .models import Service, ServiceCategory

admin.site.register(Service)
admin.site.register(ServiceCategory)