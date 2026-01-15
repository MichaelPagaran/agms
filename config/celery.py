"""
Celery configuration for AGMS project.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'generate-monthly-dues': {
        'task': 'apps.ledger.tasks.generate_monthly_dues',
        'schedule': crontab(day_of_month='1', hour='0', minute='0'),
    },
    'expire-unpaid-reservations': {
        'task': 'apps.assets.tasks.expire_unpaid_reservations',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
