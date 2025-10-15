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
from django.utils import timezone
from core.models import Applet, AppletSharedState, TrustedInstance
from core.services.crypto_utils import sign_request, get_local_instance_data

# Set up a logger for this agent
logger = logging.getLogger(__name__)

class ChatAgentService:
    """
    A backend agent service that manages the state of chat room applets.
    It handles two main responsibilities:
    1. Processing user-submitted messages.
    2. Synchronizing chat state with trusted federated peers.
    """

    def __init__(self, applet_id):
        self.applet_id = applet_id
        try:
            self.applet = Applet.objects.get(id=applet_id)
        except Applet.DoesNotExist:
            raise ValueError(f"Applet with ID {applet_id} does not exist.")
        self.poll_interval = 3 # Default poll interval in seconds

    def run(self):
        """
        Main loop for the service. Runs indefinitely.
        """
        logger.info(f"Starting ChatAgentService for Applet ID: {self.applet_id}")
        while True:
            try:
                self._synchronize_with_peers()
            except Exception as e:
                logger.error(f"Error during peer synchronization for applet {self.applet_id}: {e}")
            
            time.sleep(self.poll_interval)

    def process_update(self, update_data, user_pubkey):
        """
        Processes a state update request from a local user, like a new message.
        """
        action = update_data.get('action')
        if action == 'post_message':
            text = update_data.get('text')
            if not text or not isinstance(text, str) or len(text.strip()) == 0:
                return # Ignore empty messages

            state_obj, _ = AppletSharedState.objects.get_or_create(applet_id=self.applet_id)
            
            current_state = state_obj.state_data or {'messages': []}
            
            new_message = {
                'user': user_pubkey[:16], # Use a shortened pubkey for display
                'text': text.strip(),
                'timestamp': timezone.now().isoformat(),
            }

            current_state['messages'].append(new_message)
            # Ensure messages are always sorted chronologically
            current_state['messages'].sort(key=lambda m: m['timestamp'])

            state_obj.state_data = current_state
            state_obj.save()
            logger.info(f"Saved new message for applet {self.applet_id} from user {user_pubkey[:16]}")

    def _synchronize_with_peers(self):
        """
        Fetches the chat state from all trusted peers and merges new messages.
        """
        trusted_peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        if not trusted_peers:
            return

        logger.debug(f"Starting peer sync for applet {self.applet_id} with {trusted_peers.count()} peers.")

        for peer in trusted_peers:
            try:
                state_url = f"{peer.api_url}/api/applets/{self.applet_id}/state/"
                
                # We need to sign our request to prove our identity to the peer
                headers = sign_request(get_local_instance_data())
                
                response = requests.get(state_url, headers=headers, timeout=5)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

                remote_state_data = response.json()
                self._merge_state(remote_state_data, peer.hostname)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not connect to peer {peer.hostname} for applet {self.applet_id}: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred while syncing with {peer.hostname}: {e}")

    def _merge_state(self, remote_state, peer_hostname):
        """
        Merges messages from a remote state into the local state, avoiding duplicates.
        """
        if not remote_state or 'messages' not in remote_state:
            logger.warning(f"Received invalid state from peer {peer_hostname}")
            return

        local_state_obj, _ = AppletSharedState.objects.get_or_create(applet_id=self.applet_id)
        local_state = local_state_obj.state_data or {'messages': []}
        
        # Create a set of unique identifiers for local messages for efficient lookup
        local_message_ids = { (m['timestamp'], m['user']) for m in local_state.get('messages', []) }
        
        new_messages_found = False
        for remote_message in remote_state.get('messages', []):
            # A simple unique identifier for a message
            message_id = (remote_message.get('timestamp'), remote_message.get('user'))

            if message_id not in local_message_ids:
                local_state['messages'].append(remote_message)
                local_message_ids.add(message_id)
                new_messages_found = True

        if new_messages_found:
            # If we added new messages, re-sort the entire list and save.
            local_state['messages'].sort(key=lambda m: m['timestamp'])
            local_state_obj.state_data = local_state
            local_state_obj.save()
            logger.info(f"Merged new messages for applet {self.applet_id} from peer {peer_hostname}")
