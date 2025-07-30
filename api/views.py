# Full path: axon_bbs/api/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import logging
import json
from datetime import timedelta
from django.utils import timezone
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .serializers import UserSerializer, MessageBoardSerializer, MessageSerializer, ContentExtensionRequestSerializer, FileAttachmentSerializer
from .permissions import TrustedPeerPermission
from core.models import MessageBoard, Message, IgnoredPubkey, BannedPubkey, TrustedInstance, Alias, ContentExtensionRequest, FileAttachment
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)
User = get_user_model()

# --- Auth & Identity Views (Unchanged) ---
class RegisterView(generics.CreateAPIView): # ...
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class LogoutView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        if 'unencrypted_priv_key' in request.session:
            del request.session['unencrypted_priv_key']
        return Response({"status": "session cleared"}, status=status.HTTP_200_OK)

class UnlockIdentityView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user, password = request.user, request.data.get('password')
        if not password: return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f: salt = f.read()
            encryption_key = derive_key_from_password(password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)
            identity = identity_service.get_identity_by_name("default")
            if not identity: return Response({"error": "No default identity found."}, status=status.HTTP_404_NOT_FOUND)
            request.session['unencrypted_priv_key'] = identity['private_key']
            logger.info(f"Identity unlocked for user {user.username}")
            return Response({"status": "identity unlocked"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to unlock identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "Failed to unlock identity."}, status=status.HTTP_401_UNAUTHORIZED)

class ImportIdentityView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

# --- File Handling Views (Unchanged) ---
class FileUploadView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES: return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        uploaded_file = request.FILES['file']
        if not service_manager.bitsync_service: return Response({"error": "Sync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            manifest = service_manager.bitsync_service.create_manifest_and_store_chunks(uploaded_file.read())
            attachment = FileAttachment.objects.create(
                author=request.user, filename=uploaded_file.name, content_type=uploaded_file.content_type,
                size=uploaded_file.size, manifest=manifest
            )
            serializer = FileAttachmentSerializer(attachment)
            logger.info(f"User {request.user.username} uploaded file '{attachment.filename}' ({attachment.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to process file upload for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "Server error during file processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FileDownloadView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, file_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            attachment = FileAttachment.objects.get(id=file_id)
        except FileAttachment.DoesNotExist:
            raise Http404("File not found.")
        if not service_manager.sync_service:
            return Response({"error": "Sync service is not available."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            decrypted_data = service_manager.sync_service.get_decrypted_content(attachment.manifest)
            if decrypted_data is None:
                return Response({"error": "Failed to retrieve or decrypt file from the network."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            response = HttpResponse(decrypted_data, content_type=attachment.content_type)
            response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
            return response
        except Exception as e:
            logger.error(f"Error during file download for file {file_id}: {e}", exc_info=True)
            return Response({"error": "An error occurred while preparing the file for download."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Content & Moderation Views (PostMessageView is updated) ---
class MessageBoardListView(generics.ListAPIView): # ...
    queryset = MessageBoard.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageBoardSerializer

class MessageListView(generics.ListAPIView): # ...
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        board_id = self.kwargs['pk']
        ignored_pubkeys = IgnoredPubkey.objects.filter(user=self.request.user).values_list('pubkey', flat=True)
        return Message.objects.filter(board_id=board_id).exclude(pubkey__in=ignored_pubkeys).order_by('-created_at')

class PostMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user, subject, body, board_name, attachment_ids = request.user, request.data.get('subject'), request.data.get('body'), request.data.get('board_name', 'general'), request.data.get('attachment_ids', [])
        if not all([subject, body]): return Response({"error": "Subject and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.session.get('unencrypted_priv_key'): return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            board, _ = MessageBoard.objects.get_or_create(name=board_name)
            
            # UPDATED: Get attachment content hashes to embed in the message manifest
            attachments = FileAttachment.objects.filter(id__in=attachment_ids, author=user)
            attachment_hashes = [att.manifest['content_hash'] for att in attachments]

            message_content = {
                "subject": subject, "body": body, "board": board.name, "pubkey": user.pubkey,
                "attachment_hashes": attachment_hashes # Embed the hashes
            }
            raw_data = json.dumps(message_content).encode('utf-8')

            if service_manager.bitsync_service:
                manifest = service_manager.bitsync_service.create_manifest_and_store_chunks(raw_data)
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

# ... Other moderation views remain the same ...
class IgnorePubkeyView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        pass
class BanPubkeyView(views.APIView): # ...
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, *args, **kwargs):
        pass
class RequestContentExtensionView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        pass
class ReviewContentExtensionView(views.APIView): # ...
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, pk, *args, **kwargs):
        pass
class UnpinContentView(views.APIView): # ...
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, *args, **kwargs):
        pass

# --- BitSync Protocol Views (SyncView is updated) ---
@method_decorator(csrf_exempt, name='dispatch')
class SyncView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, *args, **kwargs):
        since_str = request.query_params.get('since')
        if not since_str: return Response({"error": "'since' timestamp is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            since_dt = timezone.datetime.fromisoformat(since_str.replace(' ', '+'))
            new_messages = Message.objects.filter(created_at__gt=since_dt, manifest__isnull=False)
            new_files = FileAttachment.objects.filter(created_at__gt=since_dt, manifest__isnull=False)
            manifests = []
            for msg in new_messages:
                # Add metadata to help the receiver process it
                msg.manifest['content_type'] = 'message'
                manifests.append(msg.manifest)
            for f in new_files:
                f.manifest['content_type'] = 'file'
                f.manifest['filename'] = f.filename
                f.manifest['content_type_val'] = f.content_type
                f.manifest['size'] = f.size
                manifests.append(f.manifest)
            return JsonResponse({"manifests": manifests}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during sync operation: {e}", exc_info=True)
            return Response({"error": "Failed to process sync request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class BitSyncHasContentView(views.APIView): # ...
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, *args, **kwargs):
        has_content = Message.objects.filter(manifest__content_hash=content_hash).exists() or \
                      FileAttachment.objects.filter(manifest__content_hash=content_hash).exists()
        return Response(status=status.HTTP_200_OK if has_content else status.HTTP_404_NOT_FOUND)

@method_decorator(csrf_exempt, name='dispatch')
class BitSyncChunkView(views.APIView): # ...
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, chunk_index, *args, **kwargs):
        if not service_manager.bitsync_service: return Response({"error": "BitSync service not available"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, chunk_index)
        if chunk_path:
            try:
                with open(chunk_path, 'rb') as f:
                    return HttpResponse(f.read(), content_type='application/octet-stream')
            except IOError: raise Http404("Chunk file not readable.")
        else: raise Http404("Chunk not found.")

