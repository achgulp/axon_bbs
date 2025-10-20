# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Full path: axon_bbs/core/agents/realtime_message_service.py

import requests
import logging
import threading
import queue
import hashlib
import base64
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from django.conf import settings
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding

logger = logging.getLogger(__name__)

class RealtimeMessageService:
    """
    Generic service for real-time message board synchronization.
    Monitors Message objects on is_realtime=True boards for low-latency federation.

    This replaces ChatAgentService and is board-agnostic - it can handle:
    - Chat messages (AxonChat)
    - Gaming leaderboards
    - Live event announcements
    - Any applet needing <1s message latency
    """

    def __init__(self, board_id, poll_interval=1, **kwargs):
        from messaging.models import MessageBoard

        logger.info(f"[RealtimeMessageService] Initializing for board_id={board_id}")
        self.board_id = board_id

        try:
            self.board = MessageBoard.objects.get(id=self.board_id)
            if not self.board.is_realtime:
                raise ValueError(f"Board '{self.board.name}' is not configured for real-time sync (is_realtime=False)")
            logger.info(f"[RealtimeMessageService] Board found: {self.board.name}, room_id: {self.board.federation_room_id}")
        except MessageBoard.DoesNotExist:
            raise ValueError(f"MessageBoard with ID {self.board_id} does not exist.")

        self.poll_interval = int(poll_interval)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.shutdown_event = threading.Event()

        # Broadcast queue system for SSE clients
        self.subscriber_queues = []
        self.subscribers_lock = threading.Lock()

        # Track last synced message to avoid re-processing
        self.last_sync_time = timezone.now()

        # Federation authentication
        self.local_instance = None
        self.private_key = None
        self._load_identity()

        logger.info(f"RealtimeMessageService initialized for board '{self.board.name}' with {self.poll_interval}s poll interval.")

    def start(self):
        """Start the service's background thread"""
        self.thread.start()
        logger.info(f"RealtimeMessageService thread started for board '{self.board.name}'")

    def stop(self):
        """Stop the service's background thread"""
        self.shutdown_event.set()
        logger.info(f"RealtimeMessageService shutting down for board '{self.board.name}'")

    def subscribe(self):
        """
        Register a new SSE client to receive updates.
        Returns a queue that will receive new Message objects.
        """
        q = queue.Queue(maxsize=50)
        with self.subscribers_lock:
            self.subscriber_queues.append(q)
            logger.debug(f"New SSE subscriber added for board '{self.board.name}'. Total: {len(self.subscriber_queues)}")
        return q

    def unsubscribe(self, q):
        """Unregister an SSE client when it disconnects"""
        with self.subscribers_lock:
            if q in self.subscriber_queues:
                self.subscriber_queues.remove(q)
                logger.debug(f"SSE subscriber removed from board '{self.board.name}'. Total: {len(self.subscriber_queues)}")

    def _load_identity(self):
        """Load local instance identity for federation authentication"""
        from core.models import TrustedInstance
        try:
            self.local_instance = TrustedInstance.objects.filter(
                encrypted_private_key__isnull=False,
                is_trusted_peer=False
            ).first()

            if self.local_instance and self.local_instance.encrypted_private_key:
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                from cryptography.fernet import Fernet
                f = Fernet(key)
                decrypted_pem = f.decrypt(self.local_instance.encrypted_private_key.encode())
                self.private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
        except Exception as e:
            logger.error(f"Failed to load local identity for realtime message service: {e}")
            self.local_instance, self.private_key = None, None

    def _get_auth_headers(self):
        """Generate authenticated headers for federation requests"""
        if not self.private_key or not self.local_instance:
            return {}

        timestamp = datetime.now(dt_timezone.utc).isoformat()
        hasher = hashlib.sha256(timestamp.encode('utf-8'))
        digest = hasher.digest()
        signature = self.private_key.sign(
            digest,
            rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return {
            'X-Pubkey': base64.b64encode(self.local_instance.pubkey.encode('utf-8')).decode('utf-8'),
            'X-Timestamp': timestamp,
            'X-Signature': base64.b64encode(signature).decode('utf-8')
        }

    def _broadcast_update(self, messages_queryset):
        """
        Push new messages to all connected SSE clients.
        Removes any queues that are full (disconnected clients).
        """
        with self.subscribers_lock:
            if not self.subscriber_queues:
                return  # No subscribers, skip

            dead_queues = []
            for q in self.subscriber_queues:
                try:
                    q.put_nowait(messages_queryset)
                except queue.Full:
                    dead_queues.append(q)

            # Clean up disconnected clients
            for q in dead_queues:
                self.subscriber_queues.remove(q)

            if dead_queues:
                logger.debug(f"Removed {len(dead_queues)} disconnected SSE clients from board '{self.board.name}'")

    def _run(self):
        """Background loop: poll for new local messages, sync with peers, broadcast to SSE clients"""
        try:
            logger.info(f"[RealtimeMessageService] Starting real-time sync loop for board '{self.board.name}', room_id: {self.board.federation_room_id}")

            while not self.shutdown_event.wait(self.poll_interval):
                try:
                    from messaging.models import Message

                    # Check for new local messages since last sync
                    new_messages = Message.objects.filter(
                        board=self.board,
                        created_at__gt=self.last_sync_time
                    ).order_by('created_at')

                    if new_messages.exists():
                        logger.info(f"[RealtimeMessageService] Found {new_messages.count()} new messages on board '{self.board.name}'")
                        logger.info(f"[RealtimeMessageService] Broadcasting to {len(self.subscriber_queues)} subscribers")
                        self.last_sync_time = new_messages.last().created_at

                        # Broadcast to local SSE subscribers
                        self._broadcast_update(new_messages)

                    # Synchronize with federated peers
                    self._synchronize_with_peers()

                except Exception as e:
                    logger.error(f"Error in RealtimeMessageService loop for board '{self.board.name}': {e}", exc_info=True)
        except Exception as e:
            logger.error(f"FATAL: RealtimeMessageService thread crashed for board '{self.board.name}': {e}", exc_info=True)

    def _synchronize_with_peers(self):
        """
        Poll federated peers for new messages.
        Uses board.trusted_peers and board.federation_room_id.
        """
        from core.models import TrustedInstance
        from messaging.models import Message

        if not self.board.federation_room_id or not self.board.trusted_peers:
            return  # No federation configured

        # Get TrustedInstance objects for the specified URLs
        trusted_peers = TrustedInstance.objects.filter(
            is_trusted_peer=True,
            web_ui_onion_url__in=self.board.trusted_peers
        )

        if not trusted_peers.exists():
            logger.debug(f"No matching trusted peers found for board '{self.board.name}'")
            return

        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

        for peer in trusted_peers:
            if not peer.web_ui_onion_url:
                continue

            try:
                # Request messages since last_sync_time
                messages_url = f"{peer.web_ui_onion_url.strip('/')}/api/realtime/rooms/{self.board.federation_room_id}/messages/"
                params = {'since': self.last_sync_time.isoformat()}

                response = requests.get(
                    messages_url,
                    headers=self._get_auth_headers(),
                    params=params,
                    proxies=proxies,
                    timeout=10
                )

                if response.status_code == 200:
                    response_data = response.json()
                    remote_messages = response_data.get('messages', [])
                    self._merge_messages(remote_messages, peer.web_ui_onion_url)
                else:
                    logger.debug(f"Peer {peer.web_ui_onion_url} returned status {response.status_code} for room {self.board.federation_room_id}")

            except requests.exceptions.RequestException as e:
                logger.debug(f"Could not connect to peer {peer.web_ui_onion_url} for room {self.board.federation_room_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error syncing with {peer.web_ui_onion_url}: {e}")

    def _merge_messages(self, remote_messages, peer_hostname):
        """
        Merge remote messages into local database.
        Deduplicates by message UUID (id field).
        """
        from messaging.models import Message
        from core.models import User
        import uuid

        if not remote_messages:
            return

        new_count = 0
        for msg_data in remote_messages:
            try:
                msg_id = uuid.UUID(msg_data['id'])

                # Check if message already exists
                if Message.objects.filter(id=msg_id).exists():
                    continue

                # Find or create author
                author = None
                if msg_data.get('author_username'):
                    author = User.objects.filter(username=msg_data['author_username']).first()

                # Create message
                Message.objects.create(
                    id=msg_id,
                    board=self.board,
                    subject=msg_data.get('subject', ''),
                    body=msg_data.get('body', ''),
                    author=author,
                    pubkey=msg_data.get('pubkey'),
                    created_at=msg_data['created_at'],
                    metadata_manifest=msg_data.get('metadata_manifest')
                )
                new_count += 1

            except Exception as e:
                logger.error(f"Error merging message from {peer_hostname}: {e}")

        if new_count > 0:
            logger.info(f"Merged {new_count} new messages for board '{self.board.name}' from peer {peer_hostname}")
            # Update last_sync_time to latest message
            latest_msg = Message.objects.filter(board=self.board).order_by('-created_at').first()
            if latest_msg:
                self.last_sync_time = latest_msg.created_at
