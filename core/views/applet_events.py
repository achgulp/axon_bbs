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

# Full path: axon_bbs/core/views/applet_events.py

import json
import queue
import logging
from django.http import StreamingHttpResponse
from applets.models import AppletSharedState
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)

def applet_event_stream(request, applet_id):
    """
    Handles the Server-Sent Events (SSE) stream for a given applet.
    This view keeps a connection open and pushes data to the client
    when the ChatAgentService broadcasts updates.

    Uses an event-driven queue system instead of database polling for efficiency.
    """
    def event_stream():
        # Get the chat agent for this applet
        agent = service_manager.game_agents.get('chat_agent')
        if not agent:
            logger.error("SSE connection attempted but chat agent is not running")
            yield "event: error\n"
            yield "data: {\"error\": \"Chat agent not running\"}\n\n"
            return

        # Subscribe to the agent's broadcast queue
        update_queue = agent.subscribe()

        try:
            # Send initial state immediately
            try:
                state = AppletSharedState.objects.get(applet_id=applet_id)
                yield f"data: {json.dumps(state.state_data)}\n\n"
                logger.info(f"SSE client connected to applet {applet_id}, sent initial state")
            except AppletSharedState.DoesNotExist:
                # No state yet, send empty messages array
                yield "data: {\"messages\": []}\n\n"
                logger.info(f"SSE client connected to applet {applet_id}, no initial state")

            # Send a connection confirmation comment to trigger onopen event
            yield ": connected\n\n"

            # Block waiting for updates from the agent
            while True:
                try:
                    # Wait up to 30 seconds for an update
                    state_data = update_queue.get(timeout=30)

                    # Push the update to the client
                    yield f"data: {json.dumps(state_data)}\n\n"

                except queue.Empty:
                    # No updates in 30 seconds, send a keepalive comment
                    # This prevents proxies and browsers from timing out
                    yield ": keepalive\n\n"

        except GeneratorExit:
            # Client disconnected
            logger.debug(f"SSE client disconnected from applet {applet_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for applet {applet_id}: {e}", exc_info=True)
        finally:
            # Always unsubscribe when the connection ends
            agent.unsubscribe(update_queue)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'  # Prevent caching
    response['X-Accel-Buffering'] = 'no'    # Nginx: disable buffering
    return response
