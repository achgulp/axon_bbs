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

# Full path: axon_bbs/core/views/realtime_federation_api.py

import logging
from datetime import datetime
from django.http import Http404
from rest_framework import views
from rest_framework.response import Response
from rest_framework import permissions
from messaging.models import MessageBoard, Message
from federation.permissions import TrustedPeerPermission

logger = logging.getLogger(__name__)


class RealtimeRoomMessagesView(views.APIView):
    """
    Federation endpoint for real-time message boards.
    Returns messages since a given timestamp for low-latency peer synchronization.

    IMPORTANT: Returns RAW UTC timestamps for federation sync.
    Timezone conversion happens at display time (SSE stream, client-facing APIs).
    """
    permission_classes = [TrustedPeerPermission]

    def get(self, request, room_id):
        """
        GET /api/realtime/rooms/{room_id}/messages/?since=2025-10-17T20:00:00Z

        Returns all messages since the 'since' timestamp.
        """
        try:
            board = MessageBoard.objects.get(federation_room_id=room_id, is_realtime=True)
        except MessageBoard.DoesNotExist:
            raise Http404("Real-time room not found")

        # Parse 'since' parameter
        since_param = request.GET.get('since')
        if since_param:
            try:
                since_timestamp = datetime.fromisoformat(since_param.replace('Z', '+00:00'))
            except ValueError:
                return Response({"error": "Invalid 'since' timestamp format"}, status=400)
        else:
            # Default: return last 50 messages if no 'since' provided
            messages = Message.objects.filter(board=board).order_by('-created_at')[:50]
            return Response({
                "room_id": room_id,
                "board_name": board.name,
                "messages": self._serialize_messages(messages)
            })

        # Query messages since timestamp
        messages = Message.objects.filter(
            board=board,
            created_at__gt=since_timestamp
        ).order_by('created_at')[:100]  # Limit to 100 messages per request

        logger.debug(f"[Federation API] Returning {messages.count()} messages for room '{room_id}' since {since_param}")

        return Response({
            "room_id": room_id,
            "board_name": board.name,
            "messages": self._serialize_messages(messages)
        })

    def _serialize_messages(self, messages_queryset):
        """
        Serialize messages for federation API.
        Returns RAW UTC timestamps (no timezone conversion).
        """
        result = []
        for msg in messages_queryset:
            result.append({
                'id': str(msg.id),
                'subject': msg.subject,
                'body': msg.body,
                'author_username': msg.author.username if msg.author else None,
                'pubkey': msg.pubkey,
                'created_at': msg.created_at.isoformat(),  # RAW UTC
                'metadata_manifest': msg.metadata_manifest
            })
        return result
