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
import json

from ..serializers import MessageBoardSerializer, MessageSerializer, PrivateMessageSerializer, PrivateMessageOutboxSerializer
from core.models import MessageBoard, Message, IgnoredPubkey, FileAttachment, PrivateMessage, User
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
        board = get_object_or_404(MessageBoard, pk=self.kwargs['pk'])
        if self.request.user.access_level < board.required_access_level:
            return Message.objects.none()
            
        ignored_pubkeys = IgnoredPubkey.objects.filter(user=self.request.user).values_list('pubkey', flat=True)
        return Message.objects.filter(board=board).exclude(pubkey__in=ignored_pubkeys).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        board = get_object_or_404(MessageBoard, pk=self.kwargs['pk'])
        if request.user.access_level < board.required_access_level:
            return Response({"detail": "You do not have permission to view this board."}, status=status.HTTP_403_FORBIDDEN)
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
            
            if user.access_level < board.required_access_level:
                return Response({"error": "You do not have permission to post on this board."}, status=status.HTTP_403_FORBIDDEN)

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
        # --- START FIX ---
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        recipient_pubkey = request.data.get('recipient_pubkey')
        subject = request.data.get('subject')
        body = request.data.get('body')

        if not all([recipient_pubkey, subject, body]):
            return Response({"error": "Recipient, subject, and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        sender = request.user
        recipient = User.objects.filter(pubkey=recipient_pubkey).first()

        try:
            pm_content = {
                "type": "pm_body",
                "sender_pubkey": sender.pubkey,
                "recipient_pubkey": recipient_pubkey,
                "subject": subject,
                "body": body,
            }
            
            # Encrypt the message for the recipient AND the sender (for their outbox)
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(
                pm_content,
                recipients_pubkeys=[recipient_pubkey, sender.pubkey]
            )

            PrivateMessage.objects.create(
                author=sender,
                recipient=recipient, # Can be null if recipient is not a local user
                sender_pubkey=sender.pubkey,
                recipient_pubkey=recipient_pubkey,
                subject=subject,
                manifest=manifest
            )
            
            logger.info(f"User '{sender.username}' sent PM to pubkey '{recipient_pubkey[:12]}...'")
            return Response({"status": "Private message sent successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to send PM from {sender.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred while sending the message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # --- END FIX ---


class PrivateMessageListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateMessageSerializer
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(recipient=self.request.user).order_by('-created_at')


class PrivateMessageOutboxView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateMessageOutboxSerializer
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(author=self.request.user).order_by('-created_at')
