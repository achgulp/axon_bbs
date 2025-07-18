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
    def __init__(self, relay_urls: list[str], tor_service: TorService):
        self.relay_urls = relay_urls  # Global default relays
        self.tor_service = tor_service
        self.websocket_map = {}  # Dict of {url: websocket} for global connections
        self.is_connected = False
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.on_event_callback: Callable[[Dict[str, Any]], Awaitable[None]] = self.default_event_handler
        logger.info(f"NostrService initialized with default relays: {', '.join(self.relay_urls)}")

    async def default_event_handler(self, event: Dict[str, Any]):
        logger.debug(f"Received Nostr event (no handler attached): {event.get('id')}")

    async def connect(self):
        if self.is_connected:
            logger.warning(f"Already connected to default relays. Skipping.")
            return
        try:
            connect_tasks = {url: self.tor_service.connect_websocket(url) for url in self.relay_urls}
            results = await asyncio.gather(*connect_tasks.values(), return_exceptions=True)
            for i, url in enumerate(connect_tasks):
                if not isinstance(results[i], Exception):
                    self.websocket_map[url] = results[i]
                    asyncio.create_task(self._listen_for_messages(results[i], url))
            self.is_connected = bool(self.websocket_map)
            connected_relays = list(self.websocket_map.keys())
            logger.info(f"Successfully connected to default Nostr relays: {', '.join(connected_relays)}")
        except Exception as e:
            logger.error(f"Failed to connect to default Nostr relays: {e}", exc_info=True)
            await self.disconnect()

    async def _listen_for_messages(self, websocket, url):
        try:
            async for message in websocket:
                try:
                    event_data = json.loads(message)
                    if event_data[0] == "EVENT":
                        await self.on_event_callback(event_data[2])
                    elif event_data[0] == "NOTICE":
                        logger.warning(f"Received NOTICE from {url}: {event_data[1]}")
                    elif event_data[0] == "OK":
                        logger.info(f"Received OK from {url}: {event_data[1:]}")
                    elif event_data[0] == "EOSE":
                        logger.debug(f"Received EOSE from {url}: {event_data[1]}")
                except Exception as e:
                    logger.error(f"Error processing message from {url}: {e}", exc_info=True)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Connection to {url} closed: {e}")
            self.websocket_map.pop(url, None)
            if not self.websocket_map:
                self.is_connected = False
        except Exception as e:
            logger.error(f"Unexpected error in listening loop for {url}: {e}", exc_info=True)
            self.websocket_map.pop(url, None)
            if not self.websocket_map:
                self.is_connected = False

    async def publish_event(self, event: Event, relays: list[str] = None):
        """
        Publishes a signed Nostr event to specified relays (or defaults).
        Dynamically connects if needed for non-default relays.
        Skips and logs failed relays without halting the process.
        """
        target_relays = relays or self.relay_urls
        if not target_relays:
            logger.error("No relays specified for publishing.")
            return False  # Return False if no success

        message = json.dumps(["EVENT", event.to_dict()])
        temp_websocket_map = {}  # {url: ws} for temp connections
        successful_relays = []

        try:
            # Connect dynamically to any non-default relays, skipping failures
            missing_relays = [url for url in target_relays if url not in self.websocket_map]
            for url in missing_relays:
                try:
                    ws = await self.tor_service.connect_websocket(url)
                    temp_websocket_map[url] = ws
                except Exception as e:
                    logger.warning(f"Skipped connection to {url} due to error: {e}")

            # Combine with global websockets
            all_ws_map = {url: self.websocket_map.get(url) for url in target_relays if url in self.websocket_map}
            all_ws_map.update(temp_websocket_map)

            # Publish to each, skipping failures
            for url, ws in all_ws_map.items():
                if ws:
                    try:
                        await ws.send(message)
                        successful_relays.append(url)
                        logger.info(f"Successfully published event {event.id} to {url}")
                    except Exception as e:
                        logger.warning(f"Failed to publish event {event.id} to {url}: {e}")

            if successful_relays:
                logger.info(f"Event {event.id} published successfully to: {', '.join(successful_relays)}")
                return True  # Success if at least one worked
            else:
                logger.error(f"Event {event.id} failed to publish to any relays.")
                return False

        except Exception as e:
            logger.error(f"Unexpected error during publish for event {event.id}: {e}", exc_info=True)
            return False
        finally:
            # Close any temporary connections
            await asyncio.gather(*[ws.close() for ws in temp_websocket_map.values()], return_exceptions=True)

    async def disconnect(self):
        disconnect_tasks = [ws.close() for ws in self.websocket_map.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        self.websocket_map = {}
        self.is_connected = False
        logger.info(f"Disconnected from all relays")
