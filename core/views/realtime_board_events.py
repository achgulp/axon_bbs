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

# Full path: axon_bbs/core/views/realtime_board_events.py

import json
import queue
import logging
import pytz
from datetime import datetime
from django.http import StreamingHttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from messaging.models import MessageBoard, Message
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)


def convert_message_timestamps(messages_queryset, user_timezone):
    """
    Convert message timestamps from UTC to user's timezone.
    Returns list of message dicts with display_time fields.
    """
    try:
        tz = pytz.timezone(user_timezone)
    except Exception as e:
        logger.warning(f"Invalid timezone '{user_timezone}': {e}, using UTC")
        tz = pytz.UTC

    result = []
    for msg in messages_queryset:
        try:
            # Convert created_at to user's timezone
            local_time = msg.created_at.astimezone(tz)
            hour = local_time.strftime('%I').lstrip('0') or '12'
            display_time = f"{hour}:{local_time.strftime('%M:%S %p')}"

            result.append({
                'id': str(msg.id),
                'subject': msg.subject,
                'body': msg.body,
                'author': msg.author.username if msg.author else 'anonymous',
                'author_nickname': msg.author.nickname if msg.author and msg.author.nickname else None,
                'avatar_url': msg.author.avatar.url if msg.author and msg.author.avatar else None,
                'created_at': msg.created_at.isoformat(),
                'display_time': display_time,
                'pubkey': msg.pubkey
            })
        except Exception as e:
            logger.error(f"Could not convert message {msg.id}: {e}")

    return result


@csrf_exempt
def realtime_board_events(request, board_id):
    """
    Generic Server-Sent Events (SSE) stream for ANY real-time message board.
    Keeps connection open and pushes new messages as they arrive.

    Supports JWT authentication via:
    1. Authorization header (Bearer token)
    2. Query parameter 'token' (for EventSource which doesn't support custom headers)
    3. Query parameter 'tz' for browser timezone detection
    """
    # Try to authenticate using JWT
    jwt_auth = JWTAuthentication()

    # Check if token is in query parameters (for EventSource)
    token_param = request.GET.get('token')
    if token_param:
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_param}'

    try:
        auth_result = jwt_auth.authenticate(request)
        if auth_result is not None:
            request.user, _ = auth_result
            logger.debug(f"[SSE] JWT authentication successful: user={request.user}")
    except (InvalidToken, Exception) as e:
        logger.debug(f"[SSE] JWT authentication failed: {e}, user will be anonymous")

    # Check if board exists and is realtime-enabled
    try:
        board = MessageBoard.objects.get(id=board_id)
        if not board.is_realtime:
            return StreamingHttpResponse(
                "data: {\"error\": \"This board is not enabled for real-time updates\"}\\n\\n",
                content_type='text/event-stream',
                status=400
            )
    except MessageBoard.DoesNotExist:
        raise Http404("Message board not found")

    logger.info(f"[SSE] Client connected to realtime board '{board.name}' (id={board_id}), user={request.user}")

    def event_stream():
        # Get realtime service for this board
        service = service_manager.realtime_services.get(board_id)
        if not service:
            logger.error(f"SSE connection attempted but no realtime service running for board '{board.name}'")
            yield "event: error\\n"
            yield "data: {\\\"error\\\": \\\"Real-time service not running for this board\\\"}\\n\\n"
            return

        # Get user's timezone
        user_timezone = request.GET.get('tz')
        if not user_timezone and request.user.is_authenticated:
            user_timezone = getattr(request.user, 'timezone', None)
        if not user_timezone:
            user_timezone = 'UTC'

        logger.debug(f"[SSE] Using timezone {user_timezone} for board '{board.name}'")

        # Subscribe to the service's broadcast queue
        update_queue = service.subscribe()

        try:
            # Send initial messages (last 50)
            initial_messages = Message.objects.filter(board=board).order_by('-created_at')[:50]
            if initial_messages.exists():
                converted = convert_message_timestamps(initial_messages, user_timezone)
                yield f"data: {json.dumps({'messages': converted})}\\n\\n"
                logger.info(f"[SSE] Sent {len(converted)} initial messages for board '{board.name}'")
            else:
                yield "data: {\\\"messages\\\": []}\\n\\n"

            # Send connection confirmation
            yield ": connected\\n\\n"

            # Wait for updates
            while True:
                try:
                    new_messages_queryset = update_queue.get(timeout=30)
                    converted = convert_message_timestamps(new_messages_queryset, user_timezone)
                    yield f"data: {json.dumps({'messages': converted})}\\n\\n"
                    logger.debug(f"[SSE] Sent {len(converted)} new messages for board '{board.name}'")

                except queue.Empty:
                    # Keepalive to prevent timeout
                    yield ": keepalive\\n\\n"

        except GeneratorExit:
            logger.debug(f"[SSE] Client disconnected from board '{board.name}'")
        except Exception as e:
            logger.error(f"Error in SSE stream for board '{board.name}': {e}", exc_info=True)
        finally:
            service.unsubscribe(update_queue)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
