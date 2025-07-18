# axon_bbs/api/routing.py
from django.urls import re_path
from .consumers import NostrRelayConsumer

websocket_urlpatterns = [
    re_path(r'ws/nostr/$', NostrRelayConsumer.as_asgi()),
]
