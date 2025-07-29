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
        user = request.user
        password = request.data.get('password')
        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f: salt = f.read()
            encryption_key = derive_key_from_password(password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)
            identity = identity_service.get_identity_by_name("default")
            if not identity: return Response({"error": "No default identity found for user."}, status=status.HTTP_404_NOT_FOUND)
            request.session['unencrypted_priv_key'] = identity['private_key']
            logger.info(f"Identity unlocked for user {user.username}")
            return Response({"status": "identity unlocked"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to unlock identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "Failed to unlock identity. Check password or system logs."}, status=status.HTTP_401_UNAUTHORIZED)

class ImportIdentityView(views.APIView): # ...
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        pass # Implementation remains the same

# --- NEW: File Upload View ---
class FileUploadView(views.APIView):
    """
    Handles file uploads. The file is received, processed by the BitSyncService
    to be encrypted and chunked, and a FileAttachment record is created.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        file_data = uploaded_file.read()

        if not service_manager.bitsync_service:
            logger.error("BitSyncService is not available for file upload.")
            return Response({"error": "Sync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            # Process the file data to create chunks and a manifest
            manifest = service_manager.bitsync_service.create_manifest_and_store_chunks(file_data)

            # Create the FileAttachment record in the database
            attachment = FileAttachment.objects.create(
                author=request.user,
                filename=uploaded_file.name,
                content_type=uploaded_file.content_type,
                size=uploaded_file.size,
                manifest=manifest
            )

            serializer = FileAttachmentSerializer(attachment)
            logger.info(f"User {request.user.username} uploaded file '{attachment.filename}' ({attachment.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to process file upload for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "A server error occurred during file processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        user = request.user
        subject = request.data.get('subject')
        body = request.data.get('body')
        board_name = request.data.get('board_name', 'general')
        # UPDATED: Get attachment IDs from the request
        attachment_ids = request.data.get('attachment_ids', [])

        if not all([subject, body]):
            return Response({"error": "Subject and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            board, _ = MessageBoard.objects.get_or_create(name=board_name)
            
            message_content = {"subject": subject, "body": body, "board": board.name, "pubkey": user.pubkey}
            raw_data = json.dumps(message_content).encode('utf-8')

            if service_manager.bitsync_service:
                manifest = service_manager.bitsync_service.create_manifest_and_store_chunks(raw_data)
                
                message = Message.objects.create(
                    board=board,
                    subject=subject,
                    body=body,
                    author=user,
                    pubkey=user.pubkey,
                    manifest=manifest
                )
                
                # UPDATED: Link the attachments to the message
                if attachment_ids:
                    # Ensure the user owns the attachments they are trying to link
                    attachments = FileAttachment.objects.filter(id__in=attachment_ids, author=user)
                    message.attachments.set(attachments)
                
                logger.info(f"New message '{subject}' with {len(attachment_ids)} attachment(s) posted.")
                return Response({"status": "message_posted_and_synced"}, status=status.HTTP_201_CREATED)
            else:
                logger.error("BitSyncService is not available.")
                return Response({"error": "Sync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            logger.error(f"Failed to post message for {user.username}: {e}", exc_info=True)
            return Response({"error": "A server error occurred while posting the message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Other moderation views remain the same
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

# --- BitSync Protocol Views (Unchanged) ---
@method_decorator(csrf_exempt, name='dispatch')
class SyncView(views.APIView): # ...
    permission_classes = [TrustedPeerPermission]
    def get(self, request, *args, **kwargs):
        pass
@method_decorator(csrf_exempt, name='dispatch')
class BitSyncHasContentView(views.APIView): # ...
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, *args, **kwargs):
        pass
@method_decorator(csrf_exempt, name='dispatch')
class BitSyncChunkView(views.APIView): # ...
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, chunk_index, *args, **kwargs):
        pass

