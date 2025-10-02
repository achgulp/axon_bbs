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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/applets/chat_agent_service.py
import threading
import time
import logging
import json
import uuid
from datetime import datetime, timezone
from django.db import transaction
from applets.models import Applet, AppletSharedState

logger = logging.getLogger(__name__)

class ChatAgentService:
    """
    Manages the state of a single chat room applet. It processes actions
    sent from the frontend and updates the AppletSharedState model.
    """
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.is_initialized = False

    def start(self):
        """Starts the agent's background thread."""
        self.thread.start()
        logger.info("Chat Agent Service thread started.")

    def stop(self):
        """Signals the agent's background thread to shut down."""
        self.shutdown_event.set()

    def _run(self):
        """
        The main loop for the agent's background thread.
        This will be used for federation logic in Phase 4.
        """
        while not self.shutdown_event.is_set():
            try:
                # Placeholder for future peer-to-peer state synchronization
                pass
            except Exception as e:
                logger.error(f"Error in Chat Agent loop: {e}", exc_info=True)
            self.shutdown_event.wait(self.poll_interval)

    @transaction.atomic
    def handle_action(self, applet, user, action):
        """
        Handles an action received from the UpdateStateView API endpoint.
        This is the primary entry point for modifying the chat state.
        """
        action_type = action.get('type')

        if action_type == 'new_message':
            # Get or create the shared state for this applet, locking the row for update.
            shared_state, _created = AppletSharedState.objects.select_for_update().get_or_create(
                applet=applet
            )

            # Prepare the new message object
            message_payload = action.get('payload', {})
            new_message = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'author_nickname': user.nickname,
                'author_pubkey': user.pubkey,
                'text': message_payload.get('text', '')[:500] # Limit message length
            }
            
            # Add the message to the history and increment the version number
            current_messages = shared_state.state_data.get('messages', [])
            current_messages.append(new_message)
            
            # Keep only the last 100 messages to prevent the state from growing indefinitely
            shared_state.state_data['messages'] = current_messages[-100:]
            
            shared_state.version += 1
            shared_state.save()
            
            logger.info(f"ChatAgent processed 'new_message' for applet '{applet.name}'. New version: {shared_state.version}")
            return {"status": "message received", "version": shared_state.version}

        else:
            logger.warning(f"ChatAgent received unknown action type: '{action_type}'")
            return {"status": "unknown action", "error": f"Action type '{action_type}' not supported."}
