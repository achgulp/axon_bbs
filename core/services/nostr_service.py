# axon_bbs/core/services/nostr_service.py
import logging
import json
import websockets
import asyncio
from typing import Any, Dict, Callable, Awaitable
from pynostr.event import Event  # Use pynostr.Event for consistency
from .tor_service import TorService
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import base64
import os

logger = logging.getLogger(__name__)

class NostrService:
    def __init__(self, relay_urls: list[str], tor_service: TorService):
        self.relay_urls = relay_urls  # Global default relays
        self.tor_service = tor_service
        self.websocket_map = {}  # Dict of {url: websocket} for global connections
        self.is_connected = False
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.on_event_callback: Callable[[Dict[str, Any]], Awaitable[None]] = self.handle_incoming_event
        logger.info(f"NostrService initialized with default relays: {', '.join(self.relay_urls)}")

    async def handle_incoming_event(self, event_dict: Dict[str, Any]):
        from core.models import MessageBoard, Message, User, BannedPubkey, TrustedInstance

        if event_dict.get('kind') != 1:
            return

        pubkey = event_dict.get('pubkey')
        if await sync_to_async(BannedPubkey.objects.filter(pubkey=pubkey).exists)():
            logger.info(f"Ignored event from banned pubkey {pubkey[:12]}...")
            return

        tags = {t[0]: t[1:] for t in event_dict.get('tags', [])}
        board_tags = tags.get('t', [])
        if not board_tags:
            return

        board_name = board_tags[0]  # Assume the first 't' tag is the board name
        try:
            board = await sync_to_async(MessageBoard.objects.get)(name=board_name)
        except MessageBoard.DoesNotExist:
            logger.debug(f"No board found for tag '{board_name}'")
            return

        content_str = event_dict['content']
        try:
            content = json.loads(content_str)
            if 'encrypted_data' in content and 'envelopes' in content:
                # Federated event: attempt decryption
                my_pubkey = (await sync_to_async(TrustedInstance.objects.first)()).pubkey  # Assume single instance key; adjust
                my_private_key = await self.decrypt_private_key()  # Method below
                decrypted_content = await self.decrypt_envelope(content, my_private_key, my_pubkey)
                if decrypted_content:
                    content = json.loads(decrypted_content)
                else:
                    logger.warning(f"Failed to decrypt federated event {event_dict['id']}")
                    return
        except json.JSONDecodeError:
            pass  # Not JSON or not federated; treat as plain

        try:
            subject = content.get('subject', '[No Subject]') if isinstance(content, dict) else '[No Subject]'
            body = content.get('body', '') if isinstance(content, dict) else content_str
            author = await sync_to_async(User.objects.filter(nostr_pubkey=pubkey).first)()
            created_at = datetime.fromtimestamp(event_dict['created_at'], tz=timezone.utc)

            _, created = await sync_to_async(Message.objects.get_or_create)(
                nostr_id=event_dict['id'],
                defaults={
                    'board': board,
                    'subject': subject,
                    'body': body,
                    'author': author,
                    'pubkey': pubkey,
                    'created_at': created_at,
                }
            )
            if created:
                logger.info(f"Stored new event {event_dict['id']} on board '{board_name}'")
            else:
                logger.debug(f"Event {event_dict['id']} already stored")
        except Exception as e:
            logger.error(f"Error storing event {event_dict['id']}: {e}", exc_info=True)

    async def decrypt_envelope(self, content: Dict, private_key_hex: str, my_pubkey: str):
        try:
            envelopes = content['envelopes']
            encrypted_data = content['encrypted_data'].encode()

            # Find envelope for my pubkey (assuming envelopes are dict with pubkey: encrypted_key)
            # Adjust if list; PRD says "list of encrypted session keys"
            for env in envelopes:
                # Decrypt each to find mine (inefficient but secure)
                try:
                    private_key = ec.derive_private_key(int(private_key_hex, 16), ec.SECP256K1())
                    shared_secret = private_key.exchange(ec.ECDH(), env['pubkey'])  # Assuming ECDH
                    sym_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'nostr').derive(shared_secret)
                    f = Fernet(base64.urlsafe_b64encode(sym_key))
                    return f.decrypt(encrypted_data).decode()
                except:
                    pass
            return None
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return None

    async def decrypt_private_key(self):
        from core.models import TrustedInstance
        instance = await sync_to_async(TrustedInstance.objects.first)()
        if not instance.encrypted_private_key:
            return None
        from django.conf import settings
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        return f.decrypt(instance.encrypted_private_key.encode()).decode()

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
            await self.subscribe()
        except Exception as e:
            logger.error(f"Failed to connect to default Nostr relays: {e}", exc_info=True)
            await self.disconnect()

    async def subscribe(self):
        from core.models import MessageBoard
        board_names = await sync_to_async(list)(MessageBoard.objects.values_list('name', flat=True))
        if not board_names:
            logger.warning("No message boards defined. Skipping subscription.")
            return

        filters = {"kinds": [1], "#t": board_names}
        message = json.dumps(["REQ", "axon-bbs", filters])
        send_tasks = [ws.send(message) for ws in self.websocket_map.values() if ws]
        await asyncio.gather(*send_tasks, return_exceptions=True)
        logger.info(f"Subscribed to events for boards: {', '.join(board_names)}")

    async def _listen_for_messages(self, websocket, url):
        try:
            async for message in websocket:
                try:
                    event_data = json.loads(message)
                    msg_type = event_data[0]
                    if msg_type == "EVENT":
                        await self.on_event_callback(event_data[2])
                    elif msg_type == "NOTICE":
                        logger.warning(f"Received NOTICE from {url}: {event_data[1]}")
                    elif msg_type == "OK":
                        logger.info(f"Received OK from {url}: {event_data[1:]}")
                    elif msg_type == "EOSE":
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

    async def publish_event(self, event: Event, relays: list[str] = None, is_federated=False):
        from core.models import TrustedInstance
        target_relays = relays or self.relay_urls
        if not target_relays:
            logger.error("No relays specified for publishing.")
            return False

        if is_federated:
            trusted_pubkeys = await sync_to_async(list)(TrustedInstance.objects.values_list('pubkey', flat=True))
            if not trusted_pubkeys:
                logger.warning("No trusted instances for federation.")
                return False

            # Generate symmetric key
            sym_key = os.urandom(32)
            sym_key_b64 = base64.urlsafe_b64encode(sym_key)
            f = Fernet(sym_key_b64)
            encrypted_content = f.encrypt(event.content.encode()).decode()

            # Encrypt sym_key for each trusted pubkey (using ECDH)
            envelopes = []
            for pubkey_hex in trusted_pubkeys:
                # Load public key
                pubkey_bytes = bytes.fromhex(pubkey_hex)
                public_key = serialization.load_der_public_key(pubkey_bytes)

                # Generate ephemeral private key for ECDH
                ephemeral_priv = ec.generate_private_key(ec.SECP256K1())
                shared_secret = ephemeral_priv.exchange(ec.ECDH(), public_key)

                # Derive key for envelope
                derived_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'nostr-envelope').derive(shared_secret)
                envelope_f = Fernet(base64.urlsafe_b64encode(derived_key))
                encrypted_sym_key = envelope_f.encrypt(sym_key).decode()
                envelopes.append(encrypted_sym_key)

            federated_content = json.dumps({
                "encrypted_data": encrypted_content,
                "envelopes": envelopes
            })
            event.content = federated_content

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
