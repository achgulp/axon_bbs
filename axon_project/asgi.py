# axon_bbs/axon_project/asgi.py
"""
ASGI config for axon_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')

# The WebSocket protocol type has been removed as it is no longer needed.
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
})
