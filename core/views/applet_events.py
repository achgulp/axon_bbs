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
import pytz
from datetime import datetime
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from applets.models import AppletSharedState
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)


def convert_timestamps_to_user_tz(state_data, user_timezone):
    """
    Convert message timestamps from UTC to user's timezone.
    Returns a modified copy of state_data with display_time fields added.
    """
    if not state_data or 'messages' not in state_data:
        return state_data

    try:
        tz = pytz.timezone(user_timezone)
    except Exception as e:
        logger.warning(f"Invalid timezone '{user_timezone}': {e}, using UTC")
        tz = pytz.UTC

    modified_data = state_data.copy()
    modified_data['messages'] = []

    for msg in state_data.get('messages', []):
        msg_copy = msg.copy()
        try:
            # Parse the UTC timestamp
            utc_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
            # Convert to user's timezone
            local_time = utc_time.astimezone(tz)
            # Format as display string (portable format without -)
            hour = local_time.strftime('%I').lstrip('0') or '12'  # Remove leading zero, handle midnight
            msg_copy['display_time'] = f"{hour}:{local_time.strftime('%M:%S %p')}"  # e.g., "8:10:51 PM"
            logger.debug(f"[SSE TZ CONVERT] UTC: {msg['timestamp']} -> {user_timezone}: {msg_copy['display_time']}")
        except Exception as e:
            logger.error(f"Could not convert timestamp {msg.get('timestamp')}: {e}")
            msg_copy['display_time'] = msg.get('timestamp', '')

        modified_data['messages'].append(msg_copy)

    return modified_data


@csrf_exempt
def applet_event_stream(request, applet_id):
    """
    Handles the Server-Sent Events (SSE) stream for a given applet.
    This view keeps a connection open and pushes data to the client
    when the ChatAgentService broadcasts updates.

    Uses an event-driven queue system instead of database polling for efficiency.

    Supports JWT authentication via:
    1. Authorization header (Bearer token)
    2. Query parameter 'token' (for EventSource which doesn't support custom headers)
    """
    # Try to authenticate using JWT
    jwt_auth = JWTAuthentication()

    # Check if token is in query parameters (for EventSource)
    token_param = request.GET.get('token')
    if token_param:
        # Temporarily add token to Authorization header for JWT authentication
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_param}'

    try:
        auth_result = jwt_auth.authenticate(request)
        if auth_result is not None:
            request.user, _ = auth_result
            logger.warning(f"[SSE DEBUG] JWT authentication successful: user={request.user}, timezone={getattr(request.user, 'timezone', 'NO ATTR')}")
    except (InvalidToken, Exception) as e:
        logger.warning(f"[SSE DEBUG] JWT authentication failed: {e}, user will be anonymous")

    logger.warning(f"[SSE DEBUG] applet_event_stream called for applet_id={applet_id}, user={request.user}, is_authenticated={request.user.is_authenticated if hasattr(request, 'user') else 'no user attr'}")

    def event_stream():
        # Get the chat agent for this applet
        agent = service_manager.game_agents.get('chat_agent')
        if not agent:
            logger.error("SSE connection attempted but chat agent is not running")
            yield "event: error\n"
            yield "data: {\"error\": \"Chat agent not running\"}\n\n"
            return

        # Get user's timezone
        user_timezone = getattr(request.user, 'timezone', None) or 'UTC'
        logger.warning(f"[SSE DEBUG] Inside event_stream generator, user={request.user}, user_timezone={user_timezone}, raw timezone value={getattr(request.user, 'timezone', 'NO ATTR')}")

        # Subscribe to the agent's broadcast queue
        update_queue = agent.subscribe()

        try:
            # Send initial state immediately
            try:
                state = AppletSharedState.objects.get(applet_id=applet_id)
                logger.warning(f"[SSE DEBUG] About to convert {len(state.state_data.get('messages', []))} messages to timezone {user_timezone}")
                converted_state = convert_timestamps_to_user_tz(state.state_data, user_timezone)
                yield f"data: {json.dumps(converted_state)}\n\n"
                logger.warning(f"[SSE DEBUG] SSE client connected to applet {applet_id}, sent initial state with timezone {user_timezone}")
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
                    logger.warning(f"[SSE DEBUG] Received update from queue, converting {len(state_data.get('messages', []))} messages to timezone {user_timezone}")

                    # Convert timestamps to user's timezone before sending
                    converted_state = convert_timestamps_to_user_tz(state_data, user_timezone)

                    # Push the update to the client
                    yield f"data: {json.dumps(converted_state)}\n\n"
                    logger.warning(f"[SSE DEBUG] Sent SSE update to client with timezone {user_timezone}")

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
