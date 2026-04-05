"""
ASGI config for AutoParts CRM project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoparts.settings')
application = get_asgi_application()
