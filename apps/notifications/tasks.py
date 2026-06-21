from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import logging

from .dispatcher import dispatcher

logger = logging.getLogger(__name__)


def _send_email_reminder(appt, message_type: str):
    """Email podsjetnik kao fallback ili primarni kanal."""
    if not appt.client.email:
        return

    subjects = {
        'reminder_24h': f'Podsjetnik: Vaš termin sutra u {appt.start_datetime:%H:%M}',
        'reminder_1h':  f'Podsjetnik: Vaš termin za sat vremena ({appt.start_datetime:%H:%M})',
        'confirmation': f'Potvrda termina — {appt.business.name}',
        'cancellation': f'Termin otkazan — {appt.business.name}',
    }
    service_name = appt.service.name if appt.service else '—'
    staff_text = f', radnik: {appt.staff.name}' if appt.staff else ''
    cancel_link = f"{settings.SITE_URL}/termin/otkazi/{appt.pk}/" if hasattr(settings, 'SITE_URL') else ''

    bodies = {
        'reminder_24h': (
            f"Poštovani {appt.client.first_name or appt.client.username},\n\n"
            f"Podsjećamo vas da imate termin sutra:\n\n"
            f"  Biznis:  {appt.business.name}\n"
            f"  Usluga:  {service_name}{staff_text}\n"
            f"  Datum:   {appt.start_datetime:%d.%m.%Y}\n"
            f"  Vrijeme: {appt.start_datetime:%H:%M}\n\n"
            f"{'Za otkazivanje: ' + cancel_link if cancel_link else ''}\n\n"
            f"Vidimo se!\nRezervišiBiH tim"
        ),
        'reminder_1h': (
            f"Poštovani {appt.client.first_name or appt.client.username},\n\n"
            f"Vaš termin počinje za sat vremena!\n\n"
            f"  Biznis:  {appt.business.name}\n"
            f"  Usluga:  {service_name}{staff_text}\n"
            f"  Vrijeme: {appt.start_datetime:%H:%M}\n\n"
            f"RezervišiBiH tim"
        ),
        'confirmation': (
            f"Poštovani {appt.client.first_name or appt.client.username},\n\n"
            f"Vaš termin je potvrđen:\n\n"
            f"  Biznis:  {appt.business.name}\n"
            f"  Usluga:  {service_name}{staff_text}\n"
            f"  Datum:   {appt.start_datetime:%d.%m.%Y}\n"
            f"  Vrijeme: {appt.start_datetime:%H:%M}\n\n"
            f"{'Za otkazivanje: ' + cancel_link if cancel_link else ''}\n\n"
            f"RezervišiBiH tim"
        ),
        'cancellation': (
            f"Poštovani {appt.client.first_name or appt.client.username},\n\n"
            f"Vaš termin u {appt.business.name} "
            f"({appt.start_datetime:%d.%m.%Y u %H:%M}) je otkazan.\n\n"
            f"RezervišiBiH tim"
        ),
    }

    try:
        send_mail(
            subject=subjects.get(message_type, 'Obavijest — RezervišiBiH'),
            message=bodies.get(message_type, ''),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appt.client.email],
            fail_silently=True,
        )
        logger.info(f"Email {message_type} → {appt.client.email}")
    except Exception as e:
        logger.error(f"Email greška: {e}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_appointment_confirmation(self, appointment_id: str):
    """Pošalji potvrdu odmah nakon rezervacije"""
    try:
        from apps.appointments.models import Appointment
        appt = Appointment.objects.select_related(
            'client', 'business', 'service', 'staff'
        ).get(id=appointment_id)

        context = _build_context(appt)
        dispatcher.send(
            user=appt.client,
            message_type='confirmation',
            context=context,
            appointment=appt
        )
    except Exception as exc:
        logger.error(f"Greška pri slanju potvrde {appointment_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def send_appointment_reminders():
    """Celery Beat — svaki sat. Šalje podsjetnike 24h i 1h unaprijed."""
    from apps.appointments.models import Appointment
    from apps.notifications.models import NotificationLog
    now = timezone.now()
    sent_24h = sent_1h = 0

    def _already_sent(appt, msg_type):
        return NotificationLog.objects.filter(
            appointment=appt,
            message_type=msg_type,
            status=NotificationLog.STATUS_SENT,
        ).exists()

    # Podsjetnik dan prije (prozor 23h–25h)
    for appt in Appointment.objects.filter(
        start_datetime__gte=now + timedelta(hours=23),
        start_datetime__lte=now + timedelta(hours=25),
        status=Appointment.STATUS_CONFIRMED,
    ).select_related('client', 'business', 'service', 'staff'):
        if not _already_sent(appt, 'reminder_24h'):
            dispatcher.send(user=appt.client, message_type='reminder_24h',
                            context=_build_context(appt), appointment=appt)
            _send_email_reminder(appt, 'reminder_24h')
            sent_24h += 1

    # Podsjetnik sat prije (prozor 45min–75min)
    for appt in Appointment.objects.filter(
        start_datetime__gte=now + timedelta(minutes=45),
        start_datetime__lte=now + timedelta(minutes=75),
        status=Appointment.STATUS_CONFIRMED,
    ).select_related('client', 'business', 'service', 'staff'):
        if not _already_sent(appt, 'reminder_1h'):
            dispatcher.send(user=appt.client, message_type='reminder_2h',
                            context=_build_context(appt), appointment=appt)
            _send_email_reminder(appt, 'reminder_1h')
            sent_1h += 1

    logger.info(f"Reminders: {sent_24h} x 24h, {sent_1h} x 1h")


@shared_task(bind=True, max_retries=3)
def send_cancellation_notification(self, appointment_id: str, cancelled_by: str = 'client'):
    """Pošalji obavijest o otkazivanju"""
    try:
        from apps.appointments.models import Appointment
        appt = Appointment.objects.select_related(
            'client', 'business', 'service'
        ).get(id=appointment_id)

        msg_type = 'cancellation' if cancelled_by == 'client' else 'cancellation_by_business'
        dispatcher.send(user=appt.client, message_type=msg_type,
                        context=_build_context(appt), appointment=appt)
        _send_email_reminder(appt, 'cancellation')
    except Exception as exc:
        raise self.retry(exc=exc)


def _build_context(appointment) -> dict:
    """Izgradi context dict iz Appointment objekta"""
    from django.urls import reverse
    cancel_url = f"https://rezervisi.ba{reverse('cancel', kwargs={'pk': appointment.pk})}"

    return {
        'client_name': appointment.client.first_name or appointment.client.username,
        'business_name': appointment.business.name,
        'service_name': appointment.service.name if appointment.service else '',
        'staff_name': appointment.staff.name if appointment.staff else '',
        'date': appointment.start_datetime.strftime('%d.%m.%Y'),
        'time': appointment.start_datetime.strftime('%H:%M'),
        'cancel_url': cancel_url,
    }
