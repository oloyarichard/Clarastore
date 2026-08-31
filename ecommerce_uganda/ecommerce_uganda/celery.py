import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_uganda.settings')

app = Celery('ecommerce_uganda')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
