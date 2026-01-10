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

# Full path: axon_bbs/core/views/kairo_api.py

import json
import queue
import logging
from django.http import JsonResponse, StreamingHttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from messaging.models import MessageBoard, Message
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)


@csrf_exempt
def post_intent(request):
    """
    Receive semantic intent from KairoKensei client and post to KairoCortex board.
    
    POST /api/kairo/intent/
    {
        "intent_id": "uuid",
        "compressed_concepts": ["fix", "engine", "vibration"],
        "context": "user typing about car repair",
        "confidence": 0.65,
        "user_state": "uncertain"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # JWT Authentication
    jwt_auth = JWTAuthentication()
    token_param = request.GET.get('token')
    if token_param:
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_param}'

    try:
        auth_result = jwt_auth.authenticate(request)
        if auth_result is not None:
            request.user, _ = auth_result
        else:
            return JsonResponse({'error': 'Authentication required'}, status=401)
    except (InvalidToken, Exception) as e:
        logger.warning(f"[KairoCortex] Authentication failed: {e}")
        return JsonResponse({'error': 'Invalid token'}, status=401)

    # Parse request body
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if 'intent_id' not in data:
            return JsonResponse({'error': 'Missing intent_id'}, status=400)
        if 'compressed_concepts' not in data:
            return JsonResponse({'error': 'Missing compressed_concepts'}, status=400)

    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON: {e}'}, status=400)

    # Get KairoCortex board
    try:
        board = MessageBoard.objects.get(name='KairoCortex')
    except MessageBoard.DoesNotExist:
        logger.error("[KairoCortex] MessageBoard 'KairoCortex' not found")
        return JsonResponse({'error': 'KairoCortex board not configured'}, status=500)

    # Create message on board
    try:
        message = Message.objects.create(
            board=board,
            subject='SemanticIntent',
            body=json.dumps(data),
            author=request.user
        )
        
        logger.info(f"[KairoCortex] Intent received: {data.get('intent_id')} from {request.user.username}")
        
        return JsonResponse({
            'status': 'queued',
            'message_id': str(message.id),
            'intent_id': data.get('intent_id')
        })

    except Exception as e:
        logger.error(f"[KairoCortex] Error creating message: {e}", exc_info=True)
        return JsonResponse({'error': 'Failed to queue intent'}, status=500)


@csrf_exempt
def cortex_events(request):
    """
    Server-Sent Events (SSE) stream for KairoCortex responses.
    KairoKensei clients connect here to receive CortexSuggestion messages.
    
    GET /api/kairo/events/?token=JWT_TOKEN
    
    Streams:
    data: {"messages": [{"id": "...", "subject": "CortexSuggestion", "body": {...}}]}
    """
    # JWT Authentication
    jwt_auth = JWTAuthentication()
    token_param = request.GET.get('token')
    if token_param:
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_param}'

    try:
        auth_result = jwt_auth.authenticate(request)
        if auth_result is not None:
            request.user, _ = auth_result
        else:
            return StreamingHttpResponse(
                'data: {"error": "Authentication required"}\\n\\n',
                content_type='text/event-stream',
                status=401
            )
    except (InvalidToken, Exception) as e:
        logger.warning(f"[KairoCortex] SSE authentication failed: {e}")
        return StreamingHttpResponse(
            'data: {"error": "Invalid token"}\\n\\n',
            content_type='text/event-stream',
            status=401
        )

    # Get KairoCortex board
    try:
        board = MessageBoard.objects.get(name='KairoCortex')
    except MessageBoard.DoesNotExist:
        return StreamingHttpResponse(
            'data: {"error": "KairoCortex board not configured"}\\n\\n',
            content_type='text/event-stream',
            status=500
        )

    logger.info(f"[KairoCortex SSE] Client connected: {request.user.username}")

    def event_stream():
        # Get realtime service for KairoCortex board
        service = service_manager.realtime_services.get(board.id)
        if not service:
            logger.error("[KairoCortex SSE] No realtime service running for KairoCortex board")
            yield 'event: error\\n'
            yield 'data: {"error": "Real-time service not running"}\\n\\n'
            return

        # Subscribe to broadcast queue
        update_queue = service.subscribe()

        try:
            # Send initial CortexSuggestion messages (last 10)
            initial_messages = Message.objects.filter(
                board=board,
                subject='CortexSuggestion'
            ).order_by('-created_at')[:10]

            if initial_messages.exists():
                messages_data = [
                    {
                        'id': str(msg.id),
                        'subject': msg.subject,
                        'body': json.loads(msg.body) if msg.body else {},
                        'created_at': msg.created_at.isoformat()
                    }
                    for msg in initial_messages
                ]
                yield f'data: {json.dumps({"messages": messages_data})}\\n\\n'
                logger.info(f"[KairoCortex SSE] Sent {len(messages_data)} initial suggestions")
            else:
                yield 'data: {"messages": []}\\n\\n'

            # Connection confirmation
            yield ': connected\\n\\n'

            # Wait for new messages
            while True:
                try:
                    new_messages_queryset = update_queue.get(timeout=30)
                    
                    # Filter for CortexSuggestion messages only
                    cortex_messages = [
                        msg for msg in new_messages_queryset 
                        if msg.subject == 'CortexSuggestion'
                    ]
                    
                    if cortex_messages:
                        messages_data = [
                            {
                                'id': str(msg.id),
                                'subject': msg.subject,
                                'body': json.loads(msg.body) if msg.body else {},
                                'created_at': msg.created_at.isoformat()
                            }
                            for msg in cortex_messages
                        ]
                        yield f'data: {json.dumps({"messages": messages_data})}\\n\\n'
                        logger.debug(f"[KairoCortex SSE] Sent {len(messages_data)} new suggestions")

                except queue.Empty:
                    # Keepalive to prevent timeout
                    yield ': keepalive\\n\\n'

        except GeneratorExit:
            logger.debug(f"[KairoCortex SSE] Client disconnected: {request.user.username}")
        except Exception as e:
            logger.error(f"[KairoCortex SSE] Error in stream: {e}", exc_info=True)
        finally:
            service.unsubscribe(update_queue)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
