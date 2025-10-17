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

# Full path: axon_bbs/core/agents/chat_agent_service.py

import time
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

# It is critical that model imports are NOT at the top level.
# We will import them inside the functions that need them.

logger = logging.getLogger(__name__)

class ChatAgentService:
    """
    A backend agent service that manages the state of chat room applets.
    It handles user messages and synchronizes state with federated peers.
    Uses event-driven SSE broadcasting for efficient local user updates.
    """

    def __init__(self, applet_id, poll_interval=5, **kwargs):
        from applets.models import Applet
        import json

        print(f"[DEBUG] ChatAgentService __init__ called with applet_id={applet_id}")
        self.applet_id = applet_id
        try:
            self.applet = Applet.objects.get(id=self.applet_id)
            print(f"[DEBUG] Applet found: {self.applet.name}")
        except Applet.DoesNotExist:
            print(f"[DEBUG] Applet {applet_id} does not exist!")
            raise ValueError(f"Applet with ID {self.applet_id} does not exist.")

        # Extract room_id from applet parameters, default to applet_id for backward compatibility
        self.room_id = self.applet_id
        if self.applet.parameters:
            try:
                params = json.loads(self.applet.parameters) if isinstance(self.applet.parameters, str) else self.applet.parameters
                self.room_id = params.get('room_id', self.applet_id)
                print(f"[DEBUG] Room ID: {self.room_id}")
            except (json.JSONDecodeError, AttributeError):
                logger.warning(f"Could not parse applet parameters, using applet_id as room_id")

        self.poll_interval = int(poll_interval)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.shutdown_event = threading.Event()

        # Broadcast queue system for SSE clients
        self.subscriber_queues = []
        self.subscribers_lock = threading.Lock()

        # Federation authentication
        self.local_instance = None
        self.private_key = None
        print(f"[DEBUG] About to load identity...")
        self._load_identity()
        print(f"[DEBUG] Identity loaded. local_instance={self.local_instance is not None}")

        logger.info(f"ChatAgentService initialized for Applet ID: {self.applet_id}, Room ID: {self.room_id} with poll interval {self.poll_interval}s.")
        print(f"[DEBUG] ChatAgentService __init__ complete")

    def start(self):
        """Start the agent's background thread"""
        print(f"[DEBUG] ChatAgentService.start() called")
        self.thread.start()
        print(f"[DEBUG] Thread.start() completed. Thread alive: {self.thread.is_alive()}")
        logger.info(f"ChatAgentService thread started for applet {self.applet_id}")

    def stop(self):
        """Stop the agent's background thread"""
        self.shutdown_event.set()
        logger.info(f"ChatAgentService shutting down for applet {self.applet_id}")

    def subscribe(self):
        """
        Register a new SSE client to receive updates.
        Returns a queue that will receive state updates.
        """
        q = queue.Queue(maxsize=50)
        with self.subscribers_lock:
            self.subscriber_queues.append(q)
            logger.debug(f"New SSE subscriber added. Total subscribers: {len(self.subscriber_queues)}")
        return q

    def unsubscribe(self, q):
        """Unregister an SSE client when it disconnects"""
        with self.subscribers_lock:
            if q in self.subscriber_queues:
                self.subscriber_queues.remove(q)
                logger.debug(f"SSE subscriber removed. Total subscribers: {len(self.subscriber_queues)}")

    def _load_identity(self):
        """Load local instance identity for authentication"""
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
            logger.error(f"Failed to load local identity for chat agent: {e}")
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

    def _broadcast_update(self, state_data):
        """
        Push state updates to all connected SSE clients.
        Removes any queues that are full (disconnected clients).
        """
        with self.subscribers_lock:
            dead_queues = []
            for q in self.subscriber_queues:
                try:
                    q.put_nowait(state_data)
                except queue.Full:
                    dead_queues.append(q)

            # Clean up disconnected clients
            for q in dead_queues:
                self.subscriber_queues.remove(q)

            if dead_queues:
                logger.debug(f"Removed {len(dead_queues)} disconnected SSE clients")

    def _run(self):
        """Background loop: poll peers and broadcast updates"""
        print(f"[DEBUG] _run() method started!")
        logger.info(f"Starting federation sync loop for Applet ID: {self.applet_id}, Room ID: {self.room_id}")
        print(f"[DEBUG] About to enter while loop...")

        while not self.shutdown_event.wait(self.poll_interval):
            print(f"[DEBUG] Inside while loop iteration")
            try:
                # Synchronize with federated peers
                self._synchronize_with_peers()

                # Only broadcast if there are active SSE subscribers
                with self.subscribers_lock:
                    has_subscribers = len(self.subscriber_queues) > 0

                if has_subscribers:
                    # Broadcast current state to all local SSE subscribers
                    from applets.models import AppletSharedState
                    try:
                        state_obj = AppletSharedState.objects.get(room_id=self.room_id)
                        self._broadcast_update(state_obj.state_data)
                    except AppletSharedState.DoesNotExist:
                        # No state yet, broadcast empty state
                        self._broadcast_update({'messages': []})

            except Exception as e:
                logger.error(f"Error during peer synchronization for room {self.room_id}: {e}", exc_info=True)

    def handle_action(self, applet, user, action_data):
        """
        Called by the UpdateStateView when a user posts a message.
        Processes the action and broadcasts to local SSE clients immediately.
        """
        action = action_data.get('action')
        if action == 'post_message':
            text = action_data.get('text')
            if not text or not isinstance(text, str) or len(text.strip()) == 0:
                return {"status": "error", "message": "Message text is required"}

            from applets.models import AppletSharedState

            state_obj, _ = AppletSharedState.objects.get_or_create(
                room_id=self.room_id,
                defaults={'applet_id': self.applet_id}
            )
            current_state = state_obj.state_data or {'messages': []}

            # Build avatar URL and short user ID
            avatar_url = None
            if user.avatar:
                avatar_url = user.avatar.url

            # Generate short user ID from pubkey hash
            user_short_id = None
            if user.pubkey:
                user_short_id = hashlib.sha256(user.pubkey.encode()).hexdigest()[:16]

            new_message = {
                'user': user.nickname or user.username,
                'user_pubkey': user_short_id,
                'avatar_url': avatar_url,
                'text': text.strip(),
                'timestamp': timezone.now().isoformat(),
            }

            current_state['messages'].append(new_message)
            current_state['messages'].sort(key=lambda m: m['timestamp'])
            state_obj.state_data = current_state
            state_obj.save()

            logger.info(f"Saved new message for room {self.room_id} from user {user.nickname or user.username}")

            # Immediately broadcast to local SSE clients (don't wait for federation poll)
            self._broadcast_update(current_state)

            return {"status": "success"}

        return {"status": "error", "message": "Unknown action"}

    def process_update(self, update_data, user_pubkey):
        """
        Legacy method for backward compatibility.
        New code should use handle_action() instead.
        """
        from applets.models import AppletSharedState

        action = update_data.get('action')
        if action == 'post_message':
            text = update_data.get('text')
            if not text or not isinstance(text, str) or len(text.strip()) == 0:
                return

            state_obj, _ = AppletSharedState.objects.get_or_create(
                room_id=self.room_id,
                defaults={'applet_id': self.applet_id}
            )
            current_state = state_obj.state_data or {'messages': []}

            # For federated messages, we don't have user object, so no avatar
            # Generate short user ID from pubkey hash
            user_short_id = hashlib.sha256(user_pubkey.encode()).hexdigest()[:16] if user_pubkey else None

            new_message = {
                'user': user_short_id or user_pubkey[:16],
                'user_pubkey': user_short_id,
                'avatar_url': None,  # Federated messages don't have avatar info yet
                'text': text.strip(),
                'timestamp': timezone.now().isoformat(),
            }

            current_state['messages'].append(new_message)
            current_state['messages'].sort(key=lambda m: m['timestamp'])
            state_obj.state_data = current_state
            state_obj.save()
            logger.info(f"Saved new message for room {self.room_id} from user {user_pubkey[:16]}")

            # Broadcast to SSE clients
            self._broadcast_update(current_state)

    def _synchronize_with_peers(self):
        """
        Poll federated peers for new chat messages.
        Only syncs with peers specified in the applet's 'trusted_peers' parameter.
        """
        from core.models import TrustedInstance
        import json

        # Get list of allowed peer onion URLs from applet parameters
        allowed_peer_urls = []
        if self.applet.parameters:
            try:
                params = json.loads(self.applet.parameters) if isinstance(self.applet.parameters, str) else self.applet.parameters
                allowed_peer_urls = params.get('trusted_peers', [])
            except (json.JSONDecodeError, AttributeError):
                logger.warning(f"Could not parse applet parameters for {self.applet_id}")
                return

        # If no trusted_peers specified, don't sync with anyone
        if not allowed_peer_urls:
            return

        # Get TrustedInstance objects for the specified URLs
        trusted_peers = TrustedInstance.objects.filter(
            is_trusted_peer=True,
            web_ui_onion_url__in=allowed_peer_urls
        )

        if not trusted_peers.exists():
            logger.debug(f"No matching trusted peers found for room {self.room_id}")
            return

        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

        for peer in trusted_peers:
            if not peer.web_ui_onion_url:
                continue

            try:
                # Use room_id instead of applet_id in the URL
                state_url = f"{peer.web_ui_onion_url.strip('/')}/api/rooms/{self.room_id}/shared_state/"

                # Authenticated request with X-Pubkey, X-Timestamp, X-Signature headers
                response = requests.get(state_url, headers=self._get_auth_headers(), proxies=proxies, timeout=10)

                if response.status_code == 200:
                    response_data = response.json()
                    # Extract state_data from the response
                    remote_state_data = response_data.get('state_data', {})
                    self._merge_state(remote_state_data, peer.web_ui_onion_url)
                else:
                    logger.debug(f"Peer {peer.web_ui_onion_url} returned status {response.status_code} for room {self.room_id}")

            except requests.exceptions.RequestException as e:
                logger.debug(f"Could not connect to peer {peer.web_ui_onion_url} for room {self.room_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error syncing with {peer.web_ui_onion_url}: {e}")

    def _merge_state(self, remote_state, peer_hostname):
        from applets.models import AppletSharedState

        if not remote_state or 'messages' not in remote_state:
            return

        local_state_obj, _ = AppletSharedState.objects.get_or_create(
            room_id=self.room_id,
            defaults={'applet_id': self.applet_id}
        )
        local_state = local_state_obj.state_data or {'messages': []}

        # Use user_pubkey + text + timestamp for deduplication (more robust than user + timestamp)
        # This handles cases where the user display name might differ across instances
        local_message_ids = {
            (m.get('user_pubkey'), m.get('text'), m.get('timestamp'))
            for m in local_state.get('messages', [])
        }

        new_messages_found = False
        for remote_message in remote_state.get('messages', []):
            message_id = (
                remote_message.get('user_pubkey'),
                remote_message.get('text'),
                remote_message.get('timestamp')
            )
            if message_id not in local_message_ids:
                # Strip display_time field if present (for backward compatibility)
                # Database should only store UTC timestamps, conversion happens at display time
                clean_message = {k: v for k, v in remote_message.items() if k != 'display_time'}
                local_state['messages'].append(clean_message)
                local_message_ids.add(message_id)
                new_messages_found = True
                logger.debug(f"Adding new message from {remote_message.get('user')}: {remote_message.get('text')[:30]}")

        if new_messages_found:
            local_state['messages'].sort(key=lambda m: m['timestamp'])
            local_state_obj.state_data = local_state
            local_state_obj.save()
            logger.info(f"Merged {len([m for m in remote_state.get('messages', []) if (m.get('user_pubkey'), m.get('text'), m.get('timestamp')) not in {(lm.get('user_pubkey'), lm.get('text'), lm.get('timestamp')) for lm in local_state.get('messages', [])[:-len(remote_state.get('messages', []))]}])} new messages for room {self.room_id} from peer {peer_hostname}")
