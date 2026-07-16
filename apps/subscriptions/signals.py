from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from apps.businesses.models import Business


@receiver(post_save, sender=Business)
def create_subscription_for_new_business(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.subscriptions.models import Subscription
    if hasattr(instance, 'subscription'):
        return

    owner_already_had_trial = Subscription.objects.filter(
        business__owner=instance.owner
    ).exclude(business=instance).exists()

    if owner_already_had_trial:
        # Probni period je vezan za korisnika, ne za biznis — vlasnik koji
        # otvara dodatni biznis ne dobija novi besplatni trial.
        Subscription.objects.create(
            business=instance,
            status=Subscription.STATUS_EXPIRED,
            trial_end=timezone.now(),
        )
    else:
        Subscription.objects.create(
            business=instance,
            trial_end=timezone.now() + relativedelta(months=6),
        )
