import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zs_integration_module.settings')

application = get_asgi_application()
