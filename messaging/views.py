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


# Full path: axon_bbs/messaging/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse, Http404
import logging
import json
import base64
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model

from .serializers import MessageBoardSerializer, MessageSerializer, PrivateMessageSerializer, PrivateMessageOutboxSerializer
from core.serializers import FileAttachmentSerializer
from .models import MessageBoard, Message, PrivateMessage
from core.models import FileAttachment, TrustedInstance, SharedLibrary
from accounts.models import IgnoredPubkey, Alias
from core.services.service_manager import service_manager
from core.services.encryption_utils import encrypt_for_recipients_only, generate_checksum, decrypt_for_recipients_only

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
            attachment_hashes = [att.metadata_manifest['content_hash'] for att in attachments if att.metadata_manifest]
            
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
            decrypted_metadata_bytes = service_manager.sync_service.get_decrypted_content(message.metadata_manifest)
            if not decrypted_metadata_bytes:
                message.decrypted_body = "[Decryption Error: Could not read metadata]"
                message.decrypted_subject = "[Encrypted]"
                continue

            metadata = json.loads(decrypted_metadata_bytes.decode('utf-8'))
            e2e_manifest = metadata.get('e2e_manifest')

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
            decrypted_metadata_bytes = service_manager.sync_service.get_decrypted_content(message.metadata_manifest)
            if not decrypted_metadata_bytes:
                message.decrypted_body = "[Decryption Error: Could not read metadata]"
                message.decrypted_subject = "[Encrypted]"
                continue

            metadata = json.loads(decrypted_metadata_bytes.decode('utf-8'))
            e2e_manifest = metadata.get('e2e_manifest')

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
            
            if content.get('type') == 'file':
                file_bytes = base64.b64decode(content.get('data', ''))
                return HttpResponse(file_bytes, content_type=content.get('content_type', 'application/octet-stream'))
            
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
        
        try:
            user = request.user
            file_content_bytes = file.read()

            file_content_payload = {
                "type": "file",
                "filename": file.name,
                "content_type": file.content_type,
                "size": file.size,
                "data": base64.b64encode(file_content_bytes).decode('ascii')
            }
            
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(file_content_payload)
            
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

def stream_content_generator(content_hash, raw_json=False):
    sync_service = service_manager.sync_service
    logger.debug(f"Starting stream for content hash: {content_hash}")

    try:
        manifest = sync_service.get_manifest_by_content_hash(content_hash)
        if not manifest:
            logger.warning(f"Stream requested for unknown content hash: {content_hash}")
            return

        decrypted_payload_bytes = sync_service.get_decrypted_content(manifest)
        if not decrypted_payload_bytes:
            logger.error(f"Failed to decrypt payload for stream: {content_hash}")
            return
        
        if raw_json:
            yield decrypted_payload_bytes
            logger.info(f"Successfully streamed raw JSON payload for hash: {content_hash}")
            return

        payload = json.loads(decrypted_payload_bytes.decode('utf-8'))

        if payload.get('type') != 'file' or 'data' not in payload:
            logger.error(f"Stream content is not a valid file payload: {content_hash}")
            return
            
        file_bytes = base64.b64decode(payload['data'])

        import io
        yield from io.BytesIO(file_bytes)
        logger.info(f"Successfully streamed {len(file_bytes)} bytes for hash: {content_hash}")

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

        is_for_verification = 'for_verification' in request.query_params
        if is_for_verification:
            content_type = 'application/json'
            generator = stream_content_generator(content_hash, raw_json=True)
        else:
            decrypted_payload_bytes = service_manager.sync_service.get_decrypted_content(manifest)
            try:
                payload = json.loads(decrypted_payload_bytes)
                content_type = payload.get('content_type', 'application/octet-stream')
            except:
                content_type = 'application/octet-stream'
            generator = stream_content_generator(content_hash)

        response = StreamingHttpResponse(
            generator,
            content_type=content_type
        )
        return response

class StreamLibraryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, library_name, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            library = SharedLibrary.objects.get(name=library_name, is_active=True)
            content_hash = library.library_file.metadata_manifest.get('content_hash')
            if not content_hash:
                raise Http404

            # CHANGE: The generator should decode the file, not send the raw manifest JSON
            generator = stream_content_generator(content_hash, raw_json=False)
            response = StreamingHttpResponse(generator, content_type='application/javascript')
            return response

        except SharedLibrary.DoesNotExist:
            raise Http404
