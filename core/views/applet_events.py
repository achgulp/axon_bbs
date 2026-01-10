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
def chat_event_stream(request):
    """
    SSE endpoint for AxonChat using RealtimeMessageService.
    Filters messages from Realtime Event Board by subject='AxonChat'.

    This uses the unified Realtime Event Board instead of a dedicated board.
    """
    # JWT authentication
    jwt_auth = JWTAuthentication()
    token_param = request.GET.get('token')
    if token_param:
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_param}'

    try:
        auth_result = jwt_auth.authenticate(request)
        if auth_result is not None:
            request.user, _ = auth_result
    except (InvalidToken, Exception) as e:
        logger.warning(f"[SSE] JWT authentication failed: {e}")

    def event_stream():
        try:
            from messaging.models import MessageBoard
            from core.services.service_manager import service_manager

            # Get Realtime Event Board (unified board for all realtime applets)
            board = MessageBoard.objects.get(name='Realtime Event Board', is_realtime=True)

            # Get the realtime service for this board
            realtime_service = service_manager.realtime_services.get(board.id)
            if not realtime_service:
                yield "event: error\n"
                yield "data: {\"error\": \"Chat service not running\"}\n\n"
                return

            # Get user's timezone
            user_timezone = request.GET.get('tz')
            if not user_timezone and request.user.is_authenticated:
                user_timezone = getattr(request.user, 'timezone', None)
            if not user_timezone:
                user_timezone = 'UTC'

            # Subscribe to updates
            update_queue = realtime_service.subscribe()

            try:
                # Send initial messages (last 50 with subject='AxonChat', in chronological order)
                from messaging.models import Message
                from core.views.realtime_board_events import convert_message_timestamps

                initial_messages = list(Message.objects.filter(
                    board=board,
                    subject='AxonChat'  # Filter by subject to get only AxonChat messages
                ).order_by('-created_at')[:50])
                # Reverse to get chronological order (oldest first)
                initial_messages.reverse()

                if initial_messages:
                    converted = convert_message_timestamps(initial_messages, user_timezone)
                    # Format as AxonChat expected format
                    chat_messages = [{
                        'id': str(msg['id']),
                        'timestamp': msg['created_at'],
                        'display_time': msg['display_time'],
                        'user': msg['author_nickname'],  # Frontend expects 'user' field
                        'user_pubkey': msg['pubkey'],
                        'text': msg['body']
                    } for msg in converted]
                    yield f"data: {json.dumps({'messages': chat_messages})}\n\n"
                else:
                    # Send empty message list for initial connection
                    yield f"data: {json.dumps({'messages': []})}\n\n"

                yield ": connected\n\n"

                # Keep track of all messages for cumulative updates
                all_messages = initial_messages.copy() if initial_messages else []

                # Wait for updates
                while True:
                    try:
                        new_messages_queryset = update_queue.get(timeout=30)
                        # Filter new messages to only AxonChat subject
                        new_chat_messages = [msg for msg in new_messages_queryset if msg.subject == 'AxonChat']

                        if new_chat_messages:
                            # Append new chat messages to the cumulative list
                            all_messages.extend(new_chat_messages)

                            # Send the complete cumulative list (frontend expects full history)
                            converted = convert_message_timestamps(all_messages, user_timezone)
                            chat_messages = [{
                                'id': str(msg['id']),
                                'timestamp': msg['created_at'],
                                'display_time': msg['display_time'],
                                'user': msg['author_nickname'],  # Frontend expects 'user' field
                                'user_pubkey': msg['pubkey'],
                                'text': msg['body']
                            } for msg in converted]
                            yield f"data: {json.dumps({'messages': chat_messages})}\n\n"
                    except queue.Empty:
                        yield ": keepalive\n\n"
            finally:
                realtime_service.unsubscribe(update_queue)

        except MessageBoard.DoesNotExist:
            yield "event: error\n"
            yield "data: {\"error\": \"Chat board not configured\"}\n\n"
        except Exception as e:
            logger.error(f"Error in chat SSE stream: {e}", exc_info=True)
            yield "event: error\n"
            yield f"data: {{\"error\": \"Server error\"}}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
def applet_event_stream(request, applet_id):
    """
    DEPRECATED: This endpoint is deprecated and will be removed in a future version.

    For chat functionality, use chat_event_stream() at /api/chat/events/ instead.
    For new applets requiring shared state, consider using MessageBoard with RealtimeMessageService.

    This legacy endpoint relied on ChatAgentService which has been removed.
    Kept for backward compatibility only.
    """
    logger.warning(f"[DEPRECATED] applet_event_stream called for applet_id={applet_id}. This endpoint is deprecated. Use /api/chat/events/ instead.")

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
    except (InvalidToken, Exception) as e:
        logger.warning(f"[SSE] JWT authentication failed: {e}")

    def event_stream():
        # Get the chat agent for this applet
        agent = service_manager.game_agents.get('chat_agent')
        if not agent:
            logger.error("SSE connection attempted but chat agent is not running")
            yield "event: error\n"
            yield "data: {\"error\": \"Chat agent not running\"}\n\n"
            return

        # Get user's timezone from three sources (in priority order):
        # 1. Query parameter 'tz' (from browser detection)
        # 2. Authenticated user's timezone setting
        # 3. Default to UTC
        user_timezone = request.GET.get('tz')
        if not user_timezone and request.user.is_authenticated:
            user_timezone = getattr(request.user, 'timezone', None)
        if not user_timezone:
            user_timezone = 'UTC'

        logger.warning(f"[SSE DEBUG] Inside event_stream generator, user={request.user}, user_timezone={user_timezone}, from_query={request.GET.get('tz')}, from_user={getattr(request.user, 'timezone', 'NO ATTR') if request.user.is_authenticated else 'N/A'}")

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
