from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta


TWOPLACES = Decimal('0.01')


def _default_price():
    return Decimal(str(getattr(settings, 'SUBSCRIPTION_MONTHLY_PRICE', '19.00'))).quantize(TWOPLACES)


def plan_amount(monthly_price, months):
    """Cijena za odabrani broj mjeseci — 12 mjeseci ide po fiksnoj godišnjoj cijeni (popust)."""
    if months == 12:
        return Decimal(str(getattr(settings, 'SUBSCRIPTION_ANNUAL_PRICE', '200.00'))).quantize(TWOPLACES)
    return (monthly_price * months).quantize(TWOPLACES)


class Subscription(models.Model):
    STATUS_TRIAL = 'trial'
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'

    STATUSES = [
        (STATUS_TRIAL, 'Probni period'),
        (STATUS_ACTIVE, 'Aktivan'),
        (STATUS_EXPIRED, 'Istekao'),
        (STATUS_CANCELLED, 'Otkazan'),
    ]

    business = models.OneToOneField(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_TRIAL)
    trial_end = models.DateTimeField()
    active_until = models.DateTimeField(null=True, blank=True)
    monthly_price = models.DecimalField(
        max_digits=8, decimal_places=2, default=_default_price
    )
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pretplata'
        verbose_name_plural = 'Pretplate'

    def __str__(self):
        return f"{self.business.name} — {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = Subscription.objects.only('trial_end', 'active_until').get(pk=self.pk)
                if old.trial_end != self.trial_end or old.active_until != self.active_until:
                    self.reminder_sent_at = None
                    update_fields = kwargs.get('update_fields')
                    if update_fields is not None:
                        kwargs['update_fields'] = set(update_fields) | {'reminder_sent_at'}
            except Subscription.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        now = timezone.now()
        if self.status == self.STATUS_TRIAL:
            return now <= self.trial_end
        if self.status == self.STATUS_ACTIVE:
            return bool(self.active_until) and now <= self.active_until
        return False

    @property
    def effective_end(self):
        if self.status == self.STATUS_TRIAL:
            return self.trial_end
        return self.active_until

    @property
    def days_remaining(self):
        end = self.effective_end
        if not end:
            return 0
        delta = end - timezone.now()
        return max(0, delta.days)

    def extend(self, months=1):
        base = max(self.active_until or timezone.now(), timezone.now())
        self.active_until = base + relativedelta(months=months)
        self.status = self.STATUS_ACTIVE
        self.save(update_fields=['active_until', 'status', 'updated_at'])

    def sync_status(self):
        """Ažuriraj status na osnovu datuma — pozivaj u middleware-u."""
        now = timezone.now()
        if self.status == self.STATUS_TRIAL and now > self.trial_end:
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=['status', 'updated_at'])
        elif (
            self.status == self.STATUS_ACTIVE
            and self.active_until
            and now > self.active_until
        ):
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=['status', 'updated_at'])


class Payment(models.Model):
    METHOD_PAYPAL = 'paypal'
    METHOD_BANK = 'bank'
    METHODS = [
        (METHOD_PAYPAL, 'PayPal'),
        (METHOD_BANK, 'Bankovna uplata'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_REJECTED = 'rejected'
    STATUSES = [
        (STATUS_PENDING, 'Na čekanju'),
        (STATUS_CONFIRMED, 'Potvrđeno'),
        (STATUS_REJECTED, 'Odbijeno'),
    ]

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name='payments'
    )
    method = models.CharField(max_length=20, choices=METHODS)
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    months = models.PositiveIntegerField(default=1)
    # PayPal order ID ili bankovna referenca
    reference = models.CharField(max_length=300, blank=True)
    proof = models.FileField(
        upload_to='payment_proofs/', blank=True, null=True,
        verbose_name='Dokaz uplate'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Uplata'
        verbose_name_plural = 'Uplate'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subscription.business.name} — {self.get_method_display()} — {self.amount} BAM"

    @property
    def bank_reference(self):
        return f"SUB-{self.subscription.id}-{self.id:05d}"
