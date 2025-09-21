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
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
import logging
import json
import base64
import hashlib
import os
from rest_framework.parsers import MultiPartParser, FormParser
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from core.services.encryption_utils import encrypt_for_recipients_only, generate_checksum, decrypt_for_recipients_only
from ..serializers import MessageBoardSerializer, MessageSerializer, PrivateMessageSerializer, PrivateMessageOutboxSerializer, FileAttachmentSerializer
from core.models import MessageBoard, Message, IgnoredPubkey, FileAttachment, PrivateMessage, User, Alias, TrustedInstance
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
            attachment_hashes = [att.metadata_manifest['content_hash'] for att in attachments]
            
            message_content = {
                "type": "message",
                "subject": subject,
                "body": body,
                "board": board.name,
                "pubkey": user.pubkey,
                "attachment_hashes": attachment_hashes
            }
            
            if service_manager.bitsync_service:
                _content_hash, metadata_manifest = service_manager.bitsync_service.create_encrypted_content(message_content)
                message = Message.objects.create(
                    board=board, subject=subject, body=body, author=user, pubkey=user.pubkey, metadata_manifest=metadata_manifest
                )
                message.attachments.set(attachments)
                logger.info(f"New message '{subject}' with {attachments.count()} attachment(s) posted.")
                return Response({"status": "message_posted_and_synced", "message_id": message.id}, status=status.HTTP_201_CREATED)
            else:
                return Response({"error": "Sync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Failed to post message for {user.username}: {e}", exc_info=True)
            return Response({"error": "Server error while posting message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SendPrivateMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        private_key = request.session.get('unencrypted_priv_key')
        if not private_key:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        identifier = request.data.get('recipient_identifier')
        subject = request.data.get('subject')
        body = request.data.get('body')
        sender = request.user

        if not all([identifier, subject, body]):
            return Response({"error": "Recipient, subject, and body are required."}, status=status.HTTP_400_BAD_REQUEST)

        recipient_pubkey = None
        recipient = User.objects.filter(Q(username__iexact=identifier) | Q(nickname__iexact=identifier)).first()
        if recipient and recipient.pubkey:
            recipient_pubkey = recipient.pubkey
        else:
            alias = Alias.objects.filter(nickname__iexact=identifier).first()
            if alias and alias.pubkey:
                recipient_pubkey = alias.pubkey
        
        if not recipient_pubkey:
            return Response({"error": f"Recipient '{identifier}' not found or has no public key."}, status=status.HTTP_404_NOT_FOUND)

        try:
            e2e_payload = json.dumps({
                "subject": subject,
                "body": body,
                "sender_pubkey": sender.pubkey,
                "recipient_pubkey": recipient_pubkey,
            })
            
            e2e_encrypted_content, e2e_manifest = encrypt_for_recipients_only(e2e_payload, [sender.pubkey, recipient_pubkey])

            metadata = {
                "type": "pm",
                "e2e_encrypted_content_b64": base64.b64encode(e2e_encrypted_content).decode('utf-8'),
                "e2e_manifest": e2e_manifest,
                "sender_pubkey": sender.pubkey,
                "recipient_pubkey": recipient_pubkey,
                "sender_pubkey_checksum": generate_checksum(sender.pubkey),
                "recipient_pubkey_checksum": generate_checksum(recipient_pubkey),
            }
            
            all_bbs_instances = list(TrustedInstance.objects.all())
            bbs_pubkeys = [inst.pubkey for inst in all_bbs_instances if inst.pubkey]
            
            _content_hash, metadata_manifest = service_manager.bitsync_service.create_encrypted_content(
                metadata,
                b_b_s_instance_pubkeys=bbs_pubkeys
            )

            PrivateMessage.objects.create(
                author=sender,
                recipient=recipient,
                sender_pubkey=sender.pubkey,
                e2e_encrypted_content=base64.b64encode(e2e_encrypted_content).decode('utf-8'),
                metadata_manifest=metadata_manifest
            )
            
            logger.info(f"User '{sender.username}' sent E2E PM to pubkey '{recipient_pubkey[:12]}...'")
            return Response({"status": "Private message sent successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to send PM from {sender.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred while sending the message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PrivateMessageListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateMessageSerializer
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(recipient=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        private_key = request.session.get('unencrypted_priv_key')
        if not private_key:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        queryset = self.get_queryset()
        for message in queryset:
            # First, decrypt the outer metadata envelope
            decrypted_metadata_bytes = service_manager.sync_service.get_decrypted_content(message.metadata_manifest)
            if not decrypted_metadata_bytes:
                message.decrypted_body = "[Decryption Error: Could not read metadata]"
                message.decrypted_subject = "[Encrypted]"
                continue

            # Now, use the decrypted metadata to get the inner E2E manifest
            metadata = json.loads(decrypted_metadata_bytes.decode('utf-8'))
            e2e_manifest = metadata.get('e2e_manifest')

            # Finally, decrypt the actual message content with the E2E manifest
            decrypted_json = decrypt_for_recipients_only(
                base64.b64decode(message.e2e_encrypted_content),
                e2e_manifest,
                private_key
            )

            if decrypted_json:
                try:
                    content = json.loads(decrypted_json)
                    message.decrypted_body = content.get('body')
                    message.decrypted_subject = content.get('subject')
                except (json.JSONDecodeError, TypeError):
                    message.decrypted_body = "[Decryption Error: Invalid E2E format]"
                    message.decrypted_subject = "[Encrypted]"
            else:
                message.decrypted_body = None
                message.decrypted_subject = "[Encrypted]"
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PrivateMessageOutboxView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateMessageOutboxSerializer
    
    def get_queryset(self):
        return PrivateMessage.objects.filter(author=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        private_key = request.session.get('unencrypted_priv_key')
        if not private_key:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
            
        queryset = self.get_queryset()
        for message in queryset:
            # First, decrypt the outer metadata envelope
            decrypted_metadata_bytes = service_manager.sync_service.get_decrypted_content(message.metadata_manifest)
            if not decrypted_metadata_bytes:
                message.decrypted_body = "[Decryption Error: Could not read metadata]"
                message.decrypted_subject = "[Encrypted]"
                continue

            # Now, use the decrypted metadata to get the inner E2E manifest
            metadata = json.loads(decrypted_metadata_bytes.decode('utf-8'))
            e2e_manifest = metadata.get('e2e_manifest')

            # Finally, decrypt the actual message content with the E2E manifest
            decrypted_json = decrypt_for_recipients_only(
                base64.b64decode(message.e2e_encrypted_content),
                e2e_manifest,
                private_key
            )

            if decrypted_json:
                try:
                    content = json.loads(decrypted_json)
                    message.decrypted_body = content.get('body')
                    message.decrypted_subject = content.get('subject')
                except (json.JSONDecodeError, TypeError):
                    message.decrypted_body = "[Decryption Error: Invalid E2E format]"
                    message.decrypted_subject = "[Encrypted]"
            else:
                message.decrypted_body = None
                message.decrypted_subject = "[Encrypted]"
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class DeletePrivateMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        try:
            message = get_object_or_404(PrivateMessage, pk=pk)

            # A user can only delete a message if they are the author OR the recipient.
            if message.author != request.user and message.recipient != request.user:
                return Response(
                    {"error": "You do not have permission to delete this message."},
                    status=status.HTTP_403_FORBIDDEN
                )

            message.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting private message {pk} for user {request.user.username}: {e}")
            return Response(
                {"error": "An unexpected error occurred while deleting the message."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DownloadContentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, content_hash, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            sync_service = service_manager.sync_service
            manifest = sync_service.get_manifest_by_content_hash(content_hash)
            
            if not manifest:
                return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)

            decrypted_bytes = sync_service.get_decrypted_content(manifest)
            
            if not decrypted_bytes:
                return Response({"error": "Could not retrieve or decrypt content."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            content = json.loads(decrypted_bytes.decode('utf-8'))
            
            if content.get('type') == 'applet_code':
                applet_code = content.get('code', '')
                return HttpResponse(applet_code, content_type='application/javascript')
            
            # This endpoint could be expanded to handle other content types like files
            return Response({"error": "Unsupported content type for direct download."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error downloading content {content_hash} for user {request.user.username}: {e}")
            return Response({"error": "An unexpected server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FileUploadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if 'file' not in request.FILES:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        # --- FIX START ---
        # The 5MB file size limit has been commented out to allow for large video uploads.
        # A production environment should implement streaming uploads or configure the webserver
        # (e.g., Nginx) to handle large request bodies gracefully.
        #
        # if file.size > 5 * 1024 * 1024: # 5MB limit for generic files
        #     return Response({"error": "File size cannot exceed 5MB."}, status=status.HTTP_400_BAD_REQUEST)
        # --- FIX END ---

        try:
            user = request.user
            file_content_bytes = file.read()

            # Create the encrypted content and manifest
            file_content_payload = {
                "type": "file",
                "filename": file.name,
                "content_type": file.content_type,
                "size": file.size,
                "data": base64.b64encode(file_content_bytes).decode('ascii')
            }
            
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(file_content_payload)
            
            # Create the FileAttachment record
            attachment = FileAttachment.objects.create(
                author=user,
                filename=file.name,
                content_type=file.content_type,
                size=file.size,
                metadata_manifest=manifest
            )

            serializer = FileAttachmentSerializer(attachment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Could not process file upload for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred during file upload."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def stream_content_generator(content_hash):
    """A generator function to fetch, decrypt, and yield chunks for streaming."""
    sync_service = service_manager.sync_service
    bitsync_service = service_manager.bitsync_service

    try:
        manifest = sync_service.get_manifest_by_content_hash(content_hash)
        if not manifest:
            logger.warning(f"Stream requested for unknown content hash: {content_hash}")
            return

        aes_key = bitsync_service.get_decrypted_aes_key(manifest)
        iv = base64.b64decode(manifest['encryption_iv'])
        
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()

        num_chunks = len(manifest.get('chunk_hashes', []))
        
        for i in range(num_chunks):
            chunk_path = bitsync_service.get_chunk_path(content_hash, i)
            
            if not os.path.exists(chunk_path):
                sync_service._download_single_chunk(manifest, i)

            if os.path.exists(chunk_path):
                with open(chunk_path, 'rb') as f:
                    encrypted_chunk = f.read()
                
                if i < num_chunks - 1:
                    yield decryptor.update(encrypted_chunk)
                else:
                    # Last chunk needs finalization and unpadding
                    final_decrypted = decryptor.update(encrypted_chunk) + decryptor.finalize()
                    unpadded_final = unpadder.update(final_decrypted) + unpadder.finalize()
                    yield unpadded_final
            else:
                logger.error(f"Failed to obtain chunk {i} for streaming {content_hash}")
                return # Abort stream if a chunk can't be found/downloaded

    except Exception as e:
        logger.error(f"Error during content stream for {content_hash}: {e}", exc_info=True)
        return

class StreamContentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, content_hash, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)

        manifest = service_manager.sync_service.get_manifest_by_content_hash(content_hash)
        if not manifest:
            return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)

        content_type = manifest.get('content_type_val', 'application/octet-stream')
        
        response = StreamingHttpResponse(
            stream_content_generator(content_hash),
            content_type=content_type
        )
        return response
