from django.contrib import admin
from .models import WorkingHours, BlockedSlot

admin.site.register(WorkingHours)
admin.site.register(BlockedSlot)