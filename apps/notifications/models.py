from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationPreference(models.Model):
    """Korisnikove preference za primanje notifikacija"""
    CHANNEL_VIBER = 'viber'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_SMS = 'sms'
    CHANNEL_EMAIL = 'email'

    CHANNELS = [
        (CHANNEL_VIBER, 'Viber'),
        (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_EMAIL, 'Email'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='notification_prefs'
    )
    preferred_channel = models.CharField(
        max_length=20, choices=CHANNELS, default=CHANNEL_VIBER
    )
    # Šta korisnik želi primati
    receive_confirmation = models.BooleanField(default=True)
    receive_reminder_24h = models.BooleanField(default=True)
    receive_reminder_2h = models.BooleanField(default=True)
    receive_cancellation = models.BooleanField(default=True)
    receive_marketing = models.BooleanField(default=False)

    # Dostupnost kanala (popunjava se pri verifikaciji)
    viber_available = models.BooleanField(default=False)
    whatsapp_available = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} → {self.get_preferred_channel_display()}"


class NotificationLog(models.Model):
    """Log svih poslanih notifikacija"""
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'
    STATUS_FALLBACK = 'fallback'

    appointment = models.ForeignKey(
        'appointments.Appointment', on_delete=models.CASCADE,
        null=True, blank=True, related_name='notifications'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.CharField(max_length=20)
    message_type = models.CharField(max_length=50)  # 'confirmation', 'reminder_24h', itd.
    status = models.CharField(max_length=20, default=STATUS_SENT)
    provider_message_id = models.CharField(max_length=200, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.channel} → {self.user} [{self.message_type}] {self.status}"

