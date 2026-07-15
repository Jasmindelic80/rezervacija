from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
from urllib.parse import urlencode
import logging

from .dispatcher import dispatcher

logger = logging.getLogger(__name__)

SITE_URL = getattr(settings, 'SITE_URL', 'https://bookbih.ba')


def _google_calendar_url(appt) -> str:
    start = appt.start_datetime.astimezone(timezone.utc)
    end = appt.end_datetime.astimezone(timezone.utc)
    service_name = appt.service.name if appt.service else 'Termin'
    location = ''
    if appt.business.address:
        location = f'{appt.business.address}, {appt.business.city}'
    params = urlencode({
        'action': 'TEMPLATE',
        'text': f'{service_name} — {appt.business.name}',
        'dates': f'{start:%Y%m%dT%H%M%SZ}/{end:%Y%m%dT%H%M%SZ}',
        'details': f'Usluga: {service_name}\nBiznis: {appt.business.name}',
        'location': location,
    })
    return f'https://calendar.google.com/calendar/render?{params}'


def _send_email(appt, message_type: str, extra_ctx: dict = None):
    if not appt.client.email:
        return

    service_name = appt.service.name if appt.service else '—'
    staff_name = appt.staff.name if appt.staff else ''
    location = f'{appt.business.address}, {appt.business.city}' if getattr(appt.business, 'address', '') else getattr(appt.business, 'city', '')
    cancel_url = f'{SITE_URL}/termin/otkazi/{appt.pk}/'
    ics_url = f'{SITE_URL}/termin/ical/{appt.pk}/'

    subjects = {
        'confirmation': f'✅ Potvrda termina — {appt.business.name}',
        'reminder_24h': f'⏰ Podsjetnik: sutra u {appt.start_datetime:%H:%M} — {appt.business.name}',
        'reminder_1h':  f'🔔 Vaš termin za sat vremena — {appt.business.name}',
        'cancellation': f'❌ Termin otkazan — {appt.business.name}',
        'reschedule':   f'🔄 Termin premješten — {appt.business.name}',
    }

    ctx = {
        'client_name':   appt.client.first_name or appt.client.username,
        'business_name': appt.business.name,
        'service_name':  service_name,
        'staff_name':    staff_name,
        'date':          appt.start_datetime.strftime('%d.%m.%Y'),
        'time':          appt.start_datetime.strftime('%H:%M'),
        'location':      location,
        'cancel_url':    cancel_url,
        'ics_url':       ics_url,
        'google_cal_url': _google_calendar_url(appt),
    }
    if extra_ctx:
        ctx.update(extra_ctx)

    if message_type == 'confirmation':
        html_body = render_to_string('emails/appointment_confirmation.html', ctx)
        text_body = (
            f"Zdravo {ctx['client_name']},\n\n"
            f"Vaš termin je potvrđen:\n"
            f"  Biznis:  {ctx['business_name']}\n"
            f"  Usluga:  {service_name}\n"
            f"  Datum:   {ctx['date']}\n"
            f"  Vrijeme: {ctx['time']}\n\n"
            f"Dodajte u kalendar: {ics_url}\n"
            f"Otkazivanje: {cancel_url}\n\n"
            f"Tim BookBiH"
        )
    elif message_type in ('reminder_24h', 'reminder_1h'):
        period = 'sutra' if message_type == 'reminder_24h' else 'za sat vremena'
        text_body = (
            f"Podsjetnik: imate termin {period}!\n\n"
            f"  Biznis:  {ctx['business_name']}\n"
            f"  Usluga:  {service_name}\n"
            f"  Datum:   {ctx['date']}\n"
            f"  Vrijeme: {ctx['time']}\n\n"
            f"Tim BookBiH"
        )
        html_body = None
    elif message_type == 'reschedule':
        old_date = ctx.get('old_date', '')
        old_time = ctx.get('old_time', '')
        text_body = (
            f"Zdravo {ctx['client_name']},\n\n"
            f"Vaš termin u {ctx['business_name']} je premješten:\n"
            f"  Prije:  {old_date} u {old_time}\n"
            f"  Sada:   {ctx['date']} u {ctx['time']}\n\n"
            f"Dodajte u kalendar: {ics_url}\n"
            f"Otkazivanje: {cancel_url}\n\n"
            f"Tim BookBiH"
        )
        html_body = None
    else:
        text_body = (
            f"Vaš termin u {ctx['business_name']} "
            f"({ctx['date']} u {ctx['time']}) je otkazan.\n\n"
            f"Tim BookBiH"
        )
        html_body = None

    try:
        email = EmailMultiAlternatives(
            subject=subjects.get(message_type, 'Obavijest — BookBiH'),
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[appt.client.email],
        )
        if html_body:
            email.attach_alternative(html_body, 'text/html')
        email.send(fail_silently=True)
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

        dispatcher.send(
            user=appt.client,
            message_type='confirmation',
            context=_build_context(appt),
            appointment=appt,
        )
        _send_email(appt, 'confirmation')
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

    for appt in Appointment.objects.filter(
        start_datetime__gte=now + timedelta(hours=23),
        start_datetime__lte=now + timedelta(hours=25),
        status=Appointment.STATUS_CONFIRMED,
    ).select_related('client', 'business', 'service', 'staff'):
        if not _already_sent(appt, 'reminder_24h'):
            dispatcher.send(user=appt.client, message_type='reminder_24h',
                            context=_build_context(appt), appointment=appt)
            _send_email(appt, 'reminder_24h')
            sent_24h += 1

    for appt in Appointment.objects.filter(
        start_datetime__gte=now + timedelta(minutes=45),
        start_datetime__lte=now + timedelta(minutes=75),
        status=Appointment.STATUS_CONFIRMED,
    ).select_related('client', 'business', 'service', 'staff'):
        if not _already_sent(appt, 'reminder_1h'):
            dispatcher.send(user=appt.client, message_type='reminder_2h',
                            context=_build_context(appt), appointment=appt)
            _send_email(appt, 'reminder_1h')
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
        _send_email(appt, 'cancellation')
    except Exception as exc:
        raise self.retry(exc=exc)


def _build_context(appointment) -> dict:
    """Izgradi context dict iz Appointment objekta"""
    from django.urls import reverse
    cancel_url = f"{SITE_URL}{reverse('cancel', kwargs={'pk': appointment.pk})}"
    return {
        'client_name': appointment.client.first_name or appointment.client.username,
        'business_name': appointment.business.name,
        'service_name': appointment.service.name if appointment.service else '',
        'staff_name': appointment.staff.name if appointment.staff else '',
        'date': appointment.start_datetime.strftime('%d.%m.%Y'),
        'time': appointment.start_datetime.strftime('%H:%M'),
        'cancel_url': cancel_url,
    }
