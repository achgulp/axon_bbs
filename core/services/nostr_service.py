# axon_bbs/core/services/nostr_service.py
import logging
import json
import websockets
import asyncio
from typing import Any, Dict, Callable, Awaitable
from pynostr.event import Event  # Use pynostr.Event for consistency
from .tor_service import TorService

logger = logging.getLogger(__name__)

class NostrService:
    def __init__(self, relay_url: str, tor_service: TorService):
        self.relay_url = relay_url
        self.tor_service = tor_service
        self.websocket = None
        self.is_connected = False
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.on_event_callback: Callable[[Dict[str, Any]], Awaitable[None]] = self.default_event_handler
        logger.info(f"NostrService initialized for relay: {self.relay_url}")

    async def default_event_handler(self, event: Dict[str, Any]):
        logger.debug(f"Received Nostr event (no handler attached): {event.get('id')}")

    async def connect(self):
        if self.is_connected:
            logger.warning(f"Already connected to {self.relay_url}. Skipping.")
            return
        try:
            self.websocket = await self.tor_service.connect_websocket(self.relay_url)
            self.is_connected = True
            logger.info(f"Successfully connected to Nostr relay: {self.relay_url}")
            asyncio.create_task(self._listen_for_messages())
        except Exception as e:
            logger.error(f"Failed to connect to Nostr relay {self.relay_url}: {e}", exc_info=True)
            self.is_connected = False

    async def _listen_for_messages(self):
        if not self.websocket: return
        try:
            async for message in self.websocket:
                try:
                    event_data = json.loads(message)
                    if event_data[0] == "EVENT":
                        await self.on_event_callback(event_data[2])
                    elif event_data[0] == "NOTICE":
                        logger.warning(f"Received NOTICE from {self.relay_url}: {event_data[1]}")
                    elif event_data[0] == "OK":
                        logger.info(f"Received OK from {self.relay_url}: {event_data[1:]}")
                    elif event_data[0] == "EOSE":
                        logger.debug(f"Received EOSE from {self.relay_url}: {event_data[1]}")
                except Exception as e:
                    logger.error(f"Error processing message from relay: {e}", exc_info=True)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Connection to {self.relay_url} closed: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"An unexpected error occurred in the listening loop: {e}", exc_info=True)
            self.is_connected = False

    async def publish_event(self, event: Event):
        """
        Publishes a signed Nostr event to the relay.
        """
        if not self.is_connected or not self.websocket:
            logger.error("Cannot publish event, not connected to relay.")
            return

        try:
            request = ["EVENT", event.to_dict()]
            await self.websocket.send(json.dumps(request))
            logger.info(f"Published event {event.id} to {self.relay_url}")
        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}", exc_info=True)

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info(f"Disconnected from {self.relay_url}")
