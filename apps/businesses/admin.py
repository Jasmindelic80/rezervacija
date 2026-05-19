from django.contrib import admin
from .models import Business, Category, Staff, Review, BusinessPhoto

admin.site.register(Business)
admin.site.register(Category)
admin.site.register(Staff)
admin.site.register(Review)