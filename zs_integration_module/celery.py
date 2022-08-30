import os
from celery import Celery

from . import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zs_integration_module.settings')

app = Celery('zs_integration_module')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


