from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


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
    """
    Celery Beat periodic task — pokreće se svakih sat vremena.
    Šalje podsjetnike za termine u sljedećih 24h i 2h.

    # celery_beat schedule u settings.py:
    # CELERY_BEAT_SCHEDULE = {
    #     'send-reminders': {
    #         'task': 'apps.notifications.tasks.send_appointment_reminders',
    #         'schedule': crontab(minute=0),  # Svaki sat
    #     },
    # }
    """
    from apps.appointments.models import Appointment
    now = timezone.now()

    # Podsjetnik 24h unaprijed (u prozoru 23h-25h od sada)
    appts_24h = Appointment.objects.filter(
        start_datetime__gte=now + timedelta(hours=23),
        start_datetime__lte=now + timedelta(hours=25),
        status=Appointment.STATUS_CONFIRMED,
    ).select_related('client', 'business', 'service', 'staff')

    for appt in appts_24h:
        # Provjeri nije li već poslan
        from apps.notifications.models import NotificationLog
        already_sent = NotificationLog.objects.filter(
            appointment=appt,
            message_type='reminder_24h',
            status=NotificationLog.STATUS_SENT
        ).exists()

        if not already_sent:
            dispatcher.send(
                user=appt.client,
                message_type='reminder_24h',
                context=_build_context(appt),
                appointment=appt
            )

    # Podsjetnik 2h unaprijed
    appts_2h = Appointment.objects.filter(
        start_datetime__gte=now + timedelta(hours=1, minutes=45),
        start_datetime__lte=now + timedelta(hours=2, minutes=15),
        status=Appointment.STATUS_CONFIRMED,
    ).select_related('client', 'business', 'service', 'staff')

    for appt in appts_2h:
        from apps.notifications.models import NotificationLog
        already_sent = NotificationLog.objects.filter(
            appointment=appt,
            message_type='reminder_2h',
            status=NotificationLog.STATUS_SENT
        ).exists()

        if not already_sent:
            dispatcher.send(
                user=appt.client,
                message_type='reminder_2h',
                context=_build_context(appt),
                appointment=appt
            )

    logger.info(
        f"Reminders: {appts_24h.count()} x 24h, {appts_2h.count()} x 2h"
    )


@shared_task(bind=True, max_retries=3)
def send_cancellation_notification(self, appointment_id: str, cancelled_by: str = 'client'):
    """Pošalji obavijest o otkazivanju"""
    try:
        from apps.appointments.models import Appointment
        appt = Appointment.objects.select_related(
            'client', 'business', 'service'
        ).get(id=appointment_id)

        msg_type = 'cancellation' if cancelled_by == 'client' else 'cancellation_by_business'
        dispatcher.send(
            user=appt.client,
            message_type=msg_type,
            context=_build_context(appt),
            appointment=appt
        )
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
