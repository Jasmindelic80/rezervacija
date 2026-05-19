# ============================================================
# requirements.txt
# ============================================================
Django>=4.2,<5.0
djangorestframework>=3.15
django-environ>=0.11
django-crispy-forms>=2.1
crispy-bootstrap5>=0.7
Pillow>=10.0
psycopg2-binary>=2.9
whitenoise>=6.6
gunicorn>=21.0
django-filter>=23.5
httpx>=0.26
celery>=5.3
redis>=5.0
django-celery-beat>=2.5
twilio>=8.0
django-phonenumber-field>=7.3
phonenumbers>=8.13


# ============================================================
# .env.example  —  kopiraj u .env i popuni vrijednosti
# ============================================================
# Osnovno
SECRET_KEY=django-insecure-PROMIJENI-OVO-OBAVEZNO
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Baza (SQLite za razvoj, PostgreSQL za produkciju)
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgres://korisnik:lozinka@localhost:5432/rezervisi_bih

# Redis + Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Infobip — Viber Business Messages
# Registracija: https://www.infobip.com/
INFOBIP_API_KEY=
INFOBIP_BASE_URL=xxxxx.api.infobip.com
VIBER_SENDER_NAME=RezervišiBiH

# Meta WhatsApp Cloud API
# Kreiranje: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=

# Twilio SMS (fallback)
# Registracija: https://www.twilio.com/
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

# Email (za admin notifikacije)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@rezervisi.ba


# ============================================================
# apps/businesses/admin.py
# ============================================================
from django.contrib import admin
from django.utils.html import format_html
from .models import Business, Category, Staff, Review, BusinessPhoto


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'slug', 'order', 'business_count')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}

    def business_count(self, obj):
        return obj.businesses.filter(is_active=True).count()
    business_count.short_description = 'Aktivnih biznisa'


class StaffInline(admin.TabularInline):
    model = Staff
    extra = 1
    fields = ('name', 'title', 'photo', 'is_active', 'order')


class ServiceInline(admin.TabularInline):
    from apps.services.models import Service
    model = Service
    extra = 1
    fields = ('name', 'duration_minutes', 'price', 'is_active')


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        'logo_preview', 'name', 'category', 'city',
        'is_active', 'is_verified', 'avg_rating', 'created_at'
    )
    list_filter = ('is_active', 'is_verified', 'category', 'city', 'entity')
    search_fields = ('name', 'owner__username', 'phone', 'address')
    list_editable = ('is_active', 'is_verified')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [StaffInline, ServiceInline]

    fieldsets = (
        ('Osnovne informacije', {
            'fields': ('owner', 'category', 'name', 'slug', 'description')
        }),
        ('Kontakt i lokacija', {
            'fields': ('address', 'city', 'canton', 'entity',
                       'latitude', 'longitude', 'phone', 'email', 'website')
        }),
        ('Društvene mreže', {
            'fields': ('instagram', 'facebook'),
            'classes': ('collapse',)
        }),
        ('Slike', {
            'fields': ('logo', 'cover_image'),
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'accepts_walk_in',
                       'appointment_interval_minutes')
        }),
        ('Metapodaci', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;'
                'border-radius:8px;object-fit:cover;">',
                obj.logo.url
            )
        return '—'
    logo_preview.short_description = 'Logo'

    def avg_rating(self, obj):
        avg = obj.average_rating()
        if avg:
            stars = '⭐' * round(avg)
            return format_html('{} <small>({:.1f})</small>', stars, avg)
        return '—'
    avg_rating.short_description = 'Ocjena'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('business', 'client', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'created_at')
    list_editable = ('is_approved',)
    search_fields = ('business__name', 'client__username', 'comment')


# ============================================================
# apps/appointments/admin.py
# ============================================================
from django.contrib import admin
from django.utils.html import format_html
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id_short', 'client', 'business', 'service',
        'start_datetime', 'status_badge', 'created_at'
    )
    list_filter = ('status', 'business', 'start_datetime')
    search_fields = (
        'client__username', 'client__first_name',
        'business__name', 'service__name'
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'start_datetime'

    fieldsets = (
        ('Termin', {
            'fields': ('id', 'business', 'service', 'staff',
                       'start_datetime', 'end_datetime')
        }),
        ('Klijent', {
            'fields': ('client', 'client_notes')
        }),
        ('Status', {
            'fields': ('status', 'cancellation_reason', 'internal_notes')
        }),
        ('Notifikacije', {
            'fields': ('reminder_sent', 'review_requested'),
            'classes': ('collapse',)
        }),
        ('Metapodaci', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'ID'

    STATUS_COLORS = {
        'pending': '#f59e0b',
        'confirmed': '#10b981',
        'cancelled_client': '#ef4444',
        'cancelled_business': '#ef4444',
        'completed': '#6b7280',
        'no_show': '#dc2626',
    }

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:4px;font-size:0.8rem">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================================
# apps/notifications/admin.py
# ============================================================
from django.contrib import admin
from .models import NotificationLog, NotificationPreference


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        'sent_at', 'user', 'channel_badge', 'message_type',
        'status', 'appointment'
    )
    list_filter = ('channel', 'status', 'message_type', 'sent_at')
    search_fields = ('user__username', 'user__phone')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'

    CHANNEL_ICONS = {
        'viber': '💜',
        'whatsapp': '💚',
        'sms': '📱',
        'email': '📧',
    }

    def channel_badge(self, obj):
        icon = self.CHANNEL_ICONS.get(obj.channel, '❓')
        return format_html('{} {}', icon, obj.channel.upper())
    channel_badge.short_description = 'Kanal'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'preferred_channel', 'viber_available',
        'whatsapp_available', 'receive_confirmation', 'receive_reminder_24h'
    )
    list_filter = ('preferred_channel', 'viber_available', 'whatsapp_available')
    search_fields = ('user__username', 'user__phone')


# ============================================================
# apps/accounts/admin.py
# ============================================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PhoneOTP


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'phone', 'phone_verified',
        'first_name', 'last_name', 'role', 'is_active', 'date_joined'
    )
    list_filter = ('role', 'phone_verified', 'is_active')
    search_fields = ('username', 'phone', 'first_name', 'last_name', 'email')

    fieldsets = UserAdmin.fieldsets + (
        ('Dodatni podaci', {
            'fields': ('role', 'phone', 'phone_verified', 'avatar', 'city')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dodatni podaci', {
            'fields': ('role', 'phone', 'phone_verified')
        }),
    )


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ('phone', 'purpose', 'verified', 'attempts', 'created_at', 'is_expired_display')
    list_filter = ('purpose', 'verified')
    readonly_fields = ('created_at',)

    def is_expired_display(self, obj):
        return '✗ Istekao' if obj.is_expired() else '✓ Validan'
    is_expired_display.short_description = 'Status'
