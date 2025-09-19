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


# Full path: axon_bbs/api/views/content_views.py

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from core.models import Message, PrivateMessage, MessageBoard
from .serializers import MessageSerializer, PrivateMessageOutboxSerializer, PrivateMessageInboxSerializer
from core.services.encryption_utils import generate_e2e_manifest
from cryptography.fernet import Fernet
import base64
import logging

logger = logging.getLogger(__name__)

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        board_id = self.kwargs.get('board_id')
        return Message.objects.filter(board_id=board_id, board__required_sl__lte=self.request.user.sl)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

# ... (other views like BoardListView, etc.)

class PrivateMessageSendView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PrivateMessageInboxSerializer  # Reuse for input validation
    
    def create(self, request, *args, **kwargs):
        recipient_username = request.data.get('recipient_username')
        subject = request.data.get('subject')
        body = request.data.get('body')
        
        recipient = get_object_or_404(User, username=recipient_username)
        
        # Client-side should send pre-encrypted, but for safety, encrypt here if not provided
        if 'encrypted_subject' not in request.data or 'encrypted_body' not in request.data:
            # Generate ephemeral AES key
            aes_key = Fernet.generate_key()
            encrypted_subject = Fernet(aes_key).encrypt(subject.encode()).decode()
            encrypted_body = Fernet(aes_key).encrypt(body.encode()).decode()
        else:
            encrypted_subject = request.data['encrypted_subject']
            encrypted_body = request.data['encrypted_body']
            # Derive AES from request if provided (in real: validate)
            aes_key = base64.urlsafe_b64decode(request.data['aes_key'] + '=' * (4 - len(request.data['aes_key']) % 4))
        
        # Always generate E2E manifest, even for local (self + recipient)
        e2e_manifest = generate_e2e_manifest(
            sender_pubkey=request.user.pubkey,
            recipient_pubkey=recipient.pubkey,
            aes_key=aes_key
        )
        
        # Create PM
        pm = PrivateMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            encrypted_subject=encrypted_subject,
            encrypted_body=encrypted_body,
            e2e_manifest=e2e_manifest  # Ensure it's set
        )
        
        logger.info(f"Created PM {pm.id} from {request.user.username} to {recipient.username}")
        return Response({'id': pm.id}, status=status.HTTP_201_CREATED)

class PrivateMessageOutboxView(generics.ListAPIView):
    serializer_class = PrivateMessageOutboxSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(sender=self.request.user).order_by('-sent_at')
    
    def list(self, request, *args, **kwargs):
        # Pass request to serializer context for decryption
        response = super().list(request, args, kwargs)
        response.data  # Triggers serialization safely
        return response

class PrivateMessageInboxView(generics.ListAPIView):
    serializer_class = PrivateMessageInboxSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(recipient=self.request.user, read_at__isnull=True).order_by('-created_at')

# ... (mark as read view, etc.)
