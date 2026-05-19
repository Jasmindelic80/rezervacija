import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Appointment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED_CLIENT = 'cancelled_client'
    STATUS_CANCELLED_BUSINESS = 'cancelled_business'
    STATUS_COMPLETED = 'completed'
    STATUS_NO_SHOW = 'no_show'

    STATUSES = [
        (STATUS_PENDING, 'Na čekanju'),
        (STATUS_CONFIRMED, 'Potvrđen'),
        (STATUS_CANCELLED_CLIENT, 'Otkazan od klijenta'),
        (STATUS_CANCELLED_BUSINESS, 'Otkazan od salona'),
        (STATUS_COMPLETED, 'Završen'),
        (STATUS_NO_SHOW, 'Nije se pojavio'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='appointments'
    )
    business = models.ForeignKey(
        'businesses.Business', on_delete=models.CASCADE,
        related_name='appointments'
    )
    service = models.ForeignKey(
        'services.Service', on_delete=models.SET_NULL,
        null=True, related_name='appointments'
    )
    staff = models.ForeignKey(
        'businesses.Staff', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='appointments'
    )

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    status = models.CharField(
        max_length=25, choices=STATUSES, default=STATUS_PENDING
    )
    client_notes = models.TextField(
        blank=True, help_text="Napomene klijenta"
    )
    internal_notes = models.TextField(
        blank=True, help_text="Interne napomene (vidljive samo biznisu)"
    )
    cancellation_reason = models.TextField(blank=True)

    reminder_sent = models.BooleanField(default=False)
    review_requested = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime']
        indexes = [
            models.Index(fields=['business', 'start_datetime']),
            models.Index(fields=['client', 'start_datetime']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return (
            f"{self.client} → {self.business.name} | "
            f"{self.start_datetime:%d.%m.%Y %H:%M} ({self.get_status_display()})"
        )

    def duration_minutes(self):
        delta = self.end_datetime - self.start_datetime
        return int(delta.total_seconds() / 60)

    def is_cancellable(self):
        from django.utils import timezone
        from datetime import timedelta
        return (
            self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED]
            and self.start_datetime > timezone.now() + timedelta(hours=2)
        )
