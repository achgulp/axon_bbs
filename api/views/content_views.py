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


# Full path: axon_bbs/api/views/content_views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
import logging

from ..serializers import MessageBoardSerializer, MessageSerializer, PrivateMessageSerializer, PrivateMessageOutboxSerializer
from core.models import MessageBoard, Message, IgnoredPubkey, FileAttachment, PrivateMessage
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)
User = get_user_model()


class MessageBoardListView(generics.ListAPIView):
    serializer_class = MessageBoardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_access_level = self.request.user.access_level
        return MessageBoard.objects.filter(
            required_access_level__lte=user_access_level
        ).order_by('name')

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        # --- START FIX ---
        # First, ensure the user has access to this board before proceeding.
        board = get_object_or_404(MessageBoard, pk=self.kwargs['pk'])
        if self.request.user.access_level < board.required_access_level:
            return Message.objects.none() # Return an empty queryset if access is denied
        # --- END FIX ---
            
        ignored_pubkeys = IgnoredPubkey.objects.filter(user=self.request.user).values_list('pubkey', flat=True)
        return Message.objects.filter(board=board).exclude(pubkey__in=ignored_pubkeys).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        # --- START FIX ---
        # Add an explicit check to return a 403 Forbidden error.
        board = get_object_or_404(MessageBoard, pk=self.kwargs['pk'])
        if request.user.access_level < board.required_access_level:
            return Response({"detail": "You do not have permission to view this board."}, status=status.HTTP_403_FORBIDDEN)
        # --- END FIX ---
        return super().list(request, *args, **kwargs)


class PostMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user, subject, body = request.user, request.data.get('subject'), request.data.get('body')
        board_name, attachment_ids = request.data.get('board_name', 'general'), request.data.get('attachment_ids', [])
        
        if not all([subject, body]):
            return Response({"error": "Subject and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            board, _ = MessageBoard.objects.get_or_create(name=board_name)
            
            # --- START FIX ---
            # Add access level check before allowing a post
            if user.access_level < board.required_access_level:
                return Response({"error": "You do not have permission to post on this board."}, status=status.HTTP_403_FORBIDDEN)
            # --- END FIX ---

            attachments = FileAttachment.objects.filter(id__in=attachment_ids, author=user)
            attachment_hashes = [att.manifest['content_hash'] for att in attachments]
            
            message_content = {
                "type": "message",
                "subject": subject,
                "body": body,
                "board": board.name,
                "pubkey": user.pubkey,
                "attachment_hashes": attachment_hashes
            }
            
            if service_manager.bitsync_service:
                _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(message_content)
                message = Message.objects.create(
                    board=board, subject=subject, body=body, author=user, pubkey=user.pubkey, manifest=manifest
                )
                message.attachments.set(attachments)
                logger.info(f"New message '{subject}' with {attachments.count()} attachment(s) posted.")
                return Response({"status": "message_posted_and_synced"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "Sync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Failed to post message for {user.username}: {e}", exc_info=True)
            return Response({"error": "Server error while posting message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SendPrivateMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


class PrivateMessageListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateMessageSerializer
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(recipient=self.request.user)


class PrivateMessageOutboxView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateMessageOutboxSerializer
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(author=self.request.user)
