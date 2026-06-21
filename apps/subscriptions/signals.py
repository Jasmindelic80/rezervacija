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
    if not hasattr(instance, 'subscription'):
        Subscription.objects.create(
            business=instance,
            trial_end=timezone.now() + relativedelta(months=6),
        )
