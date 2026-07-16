import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

REMINDER_DAYS_BEFORE = 7


@shared_task
def send_subscription_reminders():
    """Celery Beat — jednom dnevno. Email podsjetnik kad probni period/pretplata
    ističe za 7 ili manje dana, jednom po ciklusu (dok se trial_end/active_until ne promijeni)."""
    from .models import Subscription

    sent = 0
    subs = Subscription.objects.filter(
        status__in=[Subscription.STATUS_TRIAL, Subscription.STATUS_ACTIVE],
        reminder_sent_at__isnull=True,
    ).select_related('business', 'business__owner')

    for sub in subs:
        sub.sync_status()
        if not sub.is_active:
            continue
        if 0 <= sub.days_remaining <= REMINDER_DAYS_BEFORE:
            owner = sub.business.owner
            if not owner.email:
                continue
            _send_reminder_email(sub, owner)
            sub.reminder_sent_at = timezone.now()
            sub.save(update_fields=['reminder_sent_at'])
            sent += 1

    logger.info(f"Subscription reminders sent: {sent}")
    return sent


def _send_reminder_email(sub, owner):
    site_url = getattr(settings, 'SITE_URL', 'https://bookbih.ba')
    pay_url = f"{site_url}/pretplata/placanje/{sub.business.slug}/"
    label = 'probni period' if sub.status == sub.STATUS_TRIAL else 'pretplata'

    subject = f"⏰ Vaš {label} za {sub.business.name} ističe za {sub.days_remaining} dan(a)"
    body = (
        f"Zdravo {owner.first_name or owner.username},\n\n"
        f"Vaš {label} za biznis \"{sub.business.name}\" ističe za {sub.days_remaining} dan(a) "
        f"({sub.effective_end.strftime('%d.%m.%Y')}).\n\n"
        f"Aktivirajte pretplatu kako biste nastavili primati rezervacije bez prekida:\n{pay_url}\n\n"
        f"Tim BookBiH"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'BookBiH <terminbih@gmail.com>'),
            recipient_list=[owner.email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.error(f"Greška pri slanju podsjetnika pretplate ({sub.business.name}): {exc}")
