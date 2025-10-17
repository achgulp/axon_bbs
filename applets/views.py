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


# Full path: axon_bbs/applets/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
import json
import logging
import pytz
from datetime import datetime

from .serializers import AppletSerializer, HighScoreSerializer
from messaging.serializers import MessageSerializer
from federation.permissions import TrustedPeerPermission
from .models import Applet, AppletData, HighScore, AppletSharedState
from messaging.models import Message
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
            logger.debug(f"[TZ CONVERT] UTC: {msg['timestamp']} -> {user_timezone}: {msg_copy['display_time']}")
        except Exception as e:
            logger.error(f"Could not convert timestamp {msg.get('timestamp')}: {e}")
            msg_copy['display_time'] = msg.get('timestamp', '')

        modified_data['messages'].append(msg_copy)

    return modified_data


class AppletListView(generics.ListAPIView):
    queryset = Applet.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppletSerializer

class GetSaveAppletDataView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, applet_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            applet_data = AppletData.objects.get(applet_id=applet_id, owner=request.user)
            decrypted_bytes = service_manager.sync_service.get_decrypted_content(applet_data.data_manifest)
            if decrypted_bytes:
                content = json.loads(decrypted_bytes.decode('utf-8'))
                return Response(content.get('data'))
            else:
                return Response(None, status=status.HTTP_204_NO_CONTENT)
        except AppletData.DoesNotExist:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error getting applet data for {request.user.username} and applet {applet_id}: {e}")
            return Response({"error": "Could not retrieve applet data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, applet_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            applet = Applet.objects.get(id=applet_id)
            user = request.user
            new_data = request.data

            content_to_encrypt = {
                "type": "applet_data",
                "applet_id": str(applet.id),
                "owner_pubkey": user.pubkey,
                "data": new_data
            }
            
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(
                content_to_encrypt,
                recipients_pubkeys=[user.pubkey]
            )

            AppletData.objects.update_or_create(
                applet=applet,
                owner=user,
                defaults={'data_manifest': manifest}
            )
            logger.info(f"User {user.username} saved data for applet '{applet.name}'.")
            return Response({"status": "data saved successfully"}, status=status.HTTP_200_OK)
        except Applet.DoesNotExist:
            return Response({"error": "Applet not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error saving applet data for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred while saving data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HighScoreListView(generics.ListAPIView):
    serializer_class = HighScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        applet_id = self.kwargs.get('applet_id')
        return HighScore.objects.filter(applet_id=applet_id).order_by('-score')[:25]

class PostAppletEventView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, applet_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            applet = Applet.objects.get(id=applet_id)
            if not applet.event_board:
                return Response({"error": "This applet does not have an event board configured."}, status=status.HTTP_400_BAD_REQUEST)
            
            user = request.user
            subject = request.data.get('subject')
            body = request.data.get('body')
            
            message_content = { "type": "message", "subject": subject, "body": body, "board": applet.event_board.name, "pubkey": user.pubkey }
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(message_content)

            Message.objects.create(
                board=applet.event_board, 
                subject=subject, 
                body=body, 
                author=user, 
                pubkey=user.pubkey, 
                metadata_manifest=manifest,
                agent_status='pending'
            )
            return Response({"status": "event posted successfully"}, status=status.HTTP_201_CREATED)
        except Applet.DoesNotExist:
            return Response({"error": "Applet not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error posting applet event for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "Server error while posting event."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReadAppletEventsView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        applet_id = self.kwargs.get('applet_id')
        try:
            applet = Applet.objects.get(id=applet_id)
            if applet.event_board:
                return Message.objects.filter(board=applet.event_board).order_by('-created_at')[:50]
        except Applet.DoesNotExist:
            return Message.objects.none()
        return Message.objects.none()

class AppletSharedStateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated | TrustedPeerPermission]

    def get(self, request, applet_id, *args, **kwargs):
        # Get user's timezone for timestamp conversion
        user_timezone = 'UTC'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_timezone = getattr(request.user, 'timezone', 'UTC')

        username = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous'
        logger.warning(f"[TIMEZONE DEBUG] AppletSharedStateView: user={username}, timezone={user_timezone}, is_authenticated={request.user.is_authenticated if hasattr(request, 'user') else False}")

        try:
            shared_state = AppletSharedState.objects.get(applet_id=applet_id)
            # Convert timestamps to user's timezone
            converted_state_data = convert_timestamps_to_user_tz(shared_state.state_data, user_timezone)
            logger.warning(f"[TIMEZONE DEBUG] AppletSharedStateView: converted {len(converted_state_data.get('messages', []))} messages for timezone {user_timezone}")
            return Response({
                "applet_id": shared_state.applet_id,
                "version": shared_state.version,
                "state_data": converted_state_data,
                "last_updated": shared_state.last_updated
            })
        except AppletSharedState.DoesNotExist:
            raise Http404

class RoomSharedStateView(views.APIView):
    """
    Federation-friendly endpoint that uses room_id instead of applet_id.
    This allows different applet instances across BBSes to share the same chat room.
    """
    permission_classes = [permissions.IsAuthenticated | TrustedPeerPermission]

    def get(self, request, room_id, *args, **kwargs):
        # Get user's timezone for timestamp conversion
        # Check if user is authenticated (not AnonymousUser)
        user_timezone = 'UTC'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_timezone = getattr(request.user, 'timezone', 'UTC')

        username = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous'
        logger.debug(f"[TIMEZONE DEBUG] RoomSharedStateView: user={username}, timezone={user_timezone}, is_authenticated={request.user.is_authenticated if hasattr(request, 'user') else False}")

        try:
            shared_state = AppletSharedState.objects.get(room_id=room_id)
            # Convert timestamps to user's timezone
            converted_state_data = convert_timestamps_to_user_tz(shared_state.state_data, user_timezone)
            logger.debug(f"[TIMEZONE DEBUG] RoomSharedStateView: converted {len(converted_state_data.get('messages', []))} messages for timezone {user_timezone}")
            return Response({
                "room_id": shared_state.room_id,
                "applet_id": shared_state.applet_id,
                "version": shared_state.version,
                "state_data": converted_state_data,
                "last_updated": shared_state.last_updated
            })
        except AppletSharedState.DoesNotExist:
            # Return empty state for rooms that haven't been initialized yet
            return Response({
                "room_id": room_id,
                "applet_id": None,
                "version": 0,
                "state_data": {"messages": []},
                "last_updated": None
            })

class AppletStateVersionView(views.APIView):
    permission_classes = [TrustedPeerPermission]

    def get(self, request, applet_id, *args, **kwargs):
        try:
            shared_state = AppletSharedState.objects.get(applet_id=applet_id)
            return JsonResponse({"version": shared_state.version})
        except AppletSharedState.DoesNotExist:
            raise Http404

class UpdateStateView(views.APIView):
    """
    Handles high-speed state update requests from applets, passing them
    directly to a corresponding backend agent for processing.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, applet_id, *args, **kwargs):
        applet = get_object_or_404(Applet, id=applet_id)
        user = request.user
        action = request.data
        
        # This assumes the agent is named 'chat_agent'.
        # This can be made more dynamic later if needed.
        agent_instance = service_manager.game_agents.get('chat_agent')
        
        if not agent_instance:
            logger.error(f"UpdateStateView called for applet '{applet.name}', but 'chat_agent' service is not running.")
            return Response({"error": "The backend service for this applet is not available."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        try:
            response_data = agent_instance.handle_action(applet, user, action)
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in ChatAgentService while handling action for applet '{applet.name}': {e}", exc_info=True)
            return Response({"error": "An internal error occurred while processing the action."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
