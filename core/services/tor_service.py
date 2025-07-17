# axon_bbs/core/services/tor_service.py
import socket
import logging
import websockets
import asyncio
from python_socks.async_.asyncio import Proxy
from .socket_utils import original_socket_socket

logger = logging.getLogger(__name__)

class TorService:
    def __init__(self, host: str, port: int):
        self._socks_host = host
        self._socks_port = port
        self._is_active = True  # Assume active since we use per-connection proxy
        logger.info(f"TorService initialized for proxy at {self._socks_host}:{self._socks_port}")

    def activate_proxy(self) -> bool:
        # No global patch needed; we'll use per-connection proxy
        return True

    def deactivate_proxy(self) -> None:
        pass

    def is_active(self) -> bool:
        return self._is_active

    async def connect_websocket(self, uri: str, **kwargs):
        """
        Connects to a WebSocket URI using the Tor proxy.
        Uses python_socks.Proxy for remote hostname resolution.
        """
        host = uri.split('//')[1].split('/')[0]  # Extract hostname from URI
        port = 443 if uri.startswith('wss://') else 80

        proxy = Proxy.from_url(f'socks5://{self._socks_host}:{self._socks_port}')
        try:
            sock = await proxy.connect(dest_host=host, dest_port=port)
            return await websockets.connect(uri, sock=sock, server_hostname=host, **kwargs)
        except Exception as e:
            logger.error(f"Failed to connect via proxy: {e}", exc_info=True)
            raise
