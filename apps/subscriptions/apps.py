from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    name = 'apps.subscriptions'
    verbose_name = 'Pretplate'

    def ready(self):
        import apps.subscriptions.signals  # noqa
