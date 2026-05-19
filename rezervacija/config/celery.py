# ============================================================
# config/celery.py
# ============================================================
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('rezervisi_bih')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-reminders-hourly': {
        'task': 'apps.notifications.tasks.send_appointment_reminders',
        'schedule': crontab(minute=0),  # Svaki sat u :00
    },
}


# ============================================================
# config/__init__.py
# ============================================================
# Ovo osigurava da se Celery učita kad Django startuje
# from .celery import app as celery_app
# __all__ = ('celery_app',)
