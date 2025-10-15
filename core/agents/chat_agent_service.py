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
from django.utils import timezone

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

        self.applet_id = applet_id
        try:
            self.applet = Applet.objects.get(id=self.applet_id)
        except Applet.DoesNotExist:
            raise ValueError(f"Applet with ID {self.applet_id} does not exist.")

        self.poll_interval = int(poll_interval)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.shutdown_event = threading.Event()

        # Broadcast queue system for SSE clients
        self.subscriber_queues = []
        self.subscribers_lock = threading.Lock()

        logger.info(f"ChatAgentService initialized for Applet ID: {self.applet_id} with poll interval {self.poll_interval}s.")

    def start(self):
        """Start the agent's background thread"""
        self.thread.start()
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
        logger.info(f"Starting federation sync loop for Applet ID: {self.applet_id}")

        while not self.shutdown_event.wait(self.poll_interval):
            try:
                # Synchronize with federated peers
                self._synchronize_with_peers()

                # Broadcast current state to all local SSE subscribers
                from applets.models import AppletSharedState
                try:
                    state_obj = AppletSharedState.objects.get(applet_id=self.applet_id)
                    self._broadcast_update(state_obj.state_data)
                except AppletSharedState.DoesNotExist:
                    # No state yet, broadcast empty state
                    self._broadcast_update({'messages': []})

            except Exception as e:
                logger.error(f"Error during peer synchronization for applet {self.applet_id}: {e}", exc_info=True)

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

            state_obj, _ = AppletSharedState.objects.get_or_create(applet_id=self.applet_id)
            current_state = state_obj.state_data or {'messages': []}

            new_message = {
                'user': user.nickname or user.username,
                'text': text.strip(),
                'timestamp': timezone.now().isoformat(),
            }

            current_state['messages'].append(new_message)
            current_state['messages'].sort(key=lambda m: m['timestamp'])
            state_obj.state_data = current_state
            state_obj.save()

            logger.info(f"Saved new message for applet {self.applet_id} from user {user.nickname or user.username}")

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

            state_obj, _ = AppletSharedState.objects.get_or_create(applet_id=self.applet_id)
            current_state = state_obj.state_data or {'messages': []}

            new_message = {
                'user': user_pubkey[:16],
                'text': text.strip(),
                'timestamp': timezone.now().isoformat(),
            }

            current_state['messages'].append(new_message)
            current_state['messages'].sort(key=lambda m: m['timestamp'])
            state_obj.state_data = current_state
            state_obj.save()
            logger.info(f"Saved new message for applet {self.applet_id} from user {user_pubkey[:16]}")

            # Broadcast to SSE clients
            self._broadcast_update(current_state)

    def _synchronize_with_peers(self):
        """
        Poll federated peers for new chat messages.
        Simplified version - authentication is handled at the BitSync level.
        For now, just fetch state without auth (will add proper auth later).
        """
        from core.models import TrustedInstance

        trusted_peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        if not trusted_peers.exists():
            return

        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

        for peer in trusted_peers:
            if not peer.web_ui_onion_url:
                continue

            try:
                state_url = f"{peer.web_ui_onion_url.strip('/')}/api/applets/{self.applet_id}/state/"

                # TODO: Add proper authentication headers like SyncService does
                # For now, attempt unauthenticated request
                response = requests.get(state_url, proxies=proxies, timeout=10)

                if response.status_code == 200:
                    remote_state_data = response.json()
                    self._merge_state(remote_state_data, peer.web_ui_onion_url)
                else:
                    logger.debug(f"Peer {peer.web_ui_onion_url} returned status {response.status_code} for chat state")

            except requests.exceptions.RequestException as e:
                logger.debug(f"Could not connect to peer {peer.web_ui_onion_url} for applet {self.applet_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error syncing with {peer.web_ui_onion_url}: {e}")

    def _merge_state(self, remote_state, peer_hostname):
        from core.models import AppletSharedState
        
        if not remote_state or 'messages' not in remote_state:
            return

        local_state_obj, _ = AppletSharedState.objects.get_or_create(applet_id=self.applet_id)
        local_state = local_state_obj.state_data or {'messages': []}
        
        local_message_ids = { (m['timestamp'], m['user']) for m in local_state.get('messages', []) }
        
        new_messages_found = False
        for remote_message in remote_state.get('messages', []):
            message_id = (remote_message.get('timestamp'), remote_message.get('user'))
            if message_id not in local_message_ids:
                local_state['messages'].append(remote_message)
                local_message_ids.add(message_id)
                new_messages_found = True

        if new_messages_found:
            local_state['messages'].sort(key=lambda m: m['timestamp'])
            local_state_obj.state_data = local_state
            local_state_obj.save()
            logger.info(f"Merged new messages for applet {self.applet_id} from peer {peer_hostname}")
