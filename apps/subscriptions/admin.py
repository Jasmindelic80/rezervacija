from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Subscription, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('created_at', 'confirmed_at', 'bank_reference_display')
    fields = (
        'method', 'status', 'amount', 'months',
        'reference', 'bank_reference_display', 'proof', 'notes',
        'created_at', 'confirmed_at',
    )

    def bank_reference_display(self, obj):
        if obj.pk and obj.method == Payment.METHOD_BANK:
            return obj.bank_reference
        return '-'
    bank_reference_display.short_description = 'Referentni broj (banka)'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'business', 'status_badge', 'trial_end', 'active_until',
        'days_remaining', 'monthly_price', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('business__name', 'business__owner__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PaymentInline]

    def status_badge(self, obj):
        colors = {
            'trial': '#0d6efd',
            'active': '#198754',
            'expired': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#333')
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def days_remaining(self, obj):
        return f'{obj.days_remaining} dana'
    days_remaining.short_description = 'Preostalo'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'subscription', 'method', 'status_badge', 'amount', 'months',
        'reference', 'created_at', 'confirmed_at',
    )
    list_filter = ('method', 'status')
    search_fields = ('subscription__business__name', 'reference')
    readonly_fields = ('created_at', 'bank_reference_display')
    actions = ['confirm_payments', 'reject_payments']

    def bank_reference_display(self, obj):
        return obj.bank_reference if obj.pk else '-'
    bank_reference_display.short_description = 'Referentni broj (banka)'

    def status_badge(self, obj):
        colors = {
            'pending': '#fd7e14',
            'confirmed': '#198754',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.status, '#333')
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    @admin.action(description='Potvrdi odabrane uplate i aktiviraj pretplatu')
    def confirm_payments(self, request, queryset):
        count = 0
        for payment in queryset.filter(status=Payment.STATUS_PENDING):
            payment.status = Payment.STATUS_CONFIRMED
            payment.confirmed_at = timezone.now()
            payment.save(update_fields=['status', 'confirmed_at'])
            payment.subscription.extend(months=payment.months)
            count += 1
        self.message_user(request, f'Potvrđeno {count} uplata.')

    @admin.action(description='Odbij odabrane uplate')
    def reject_payments(self, request, queryset):
        count = queryset.filter(status=Payment.STATUS_PENDING).update(
            status=Payment.STATUS_REJECTED
        )
        self.message_user(request, f'Odbijeno {count} uplata.')
