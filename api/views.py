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

# --- Auth & Identity Views ---
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        if 'unencrypted_priv_key' in request.session:
            del request.session['unencrypted_priv_key']
        return Response({"status": "session cleared"}, status=status.HTTP_200_OK)

class UnlockIdentityView(views.APIView):
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

class ImportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        # Implementation can be added here later
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

# --- File Upload View ---
class FileUploadView(views.APIView):
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
            manifest = service_manager.bitsync_service.create_manifest_and_store_chunks(file_data)
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

# --- Content & Moderation Views ---
class MessageBoardListView(generics.ListAPIView):
    queryset = MessageBoard.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageBoardSerializer

class MessageListView(generics.ListAPIView):
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
                    board=board, subject=subject, body=body, author=user, pubkey=user.pubkey, manifest=manifest
                )
                if attachment_ids:
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

class IgnorePubkeyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        pubkey = request.data.get('pubkey')
        if not pubkey: return Response({"error": "Pubkey to ignore is required."}, status=status.HTTP_400_BAD_REQUEST)
        IgnoredPubkey.objects.get_or_create(user=request.user, pubkey=pubkey)
        return Response({"status": "Pubkey ignored."}, status=status.HTTP_200_OK)

class BanPubkeyView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, *args, **kwargs):
        pubkey, is_temporary, duration_hours = request.data.get('pubkey'), request.data.get('is_temporary', False), request.data.get('duration_hours')
        if not pubkey: return Response({"error": "Pubkey to ban is required."}, status=status.HTTP_400_BAD_REQUEST)
        expires_at = None
        if is_temporary:
            if not duration_hours: return Response({"error": "Duration in hours is required for a temporary ban."}, status=status.HTTP_400_BAD_REQUEST)
            try: expires_at = timezone.now() + timedelta(hours=int(duration_hours))
            except (ValueError, TypeError): return Response({"error": "Invalid duration format."}, status=status.HTTP_400_BAD_REQUEST)
        BannedPubkey.objects.update_or_create(pubkey=pubkey, defaults={'is_temporary': is_temporary, 'expires_at': expires_at})
        status_msg = f"Pubkey temporarily banned until {expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')}." if is_temporary else "Pubkey permanently banned."
        return Response({"status": status_msg}, status=status.HTTP_200_OK)

class RequestContentExtensionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        content_id, content_type = request.data.get('content_id'), request.data.get('content_type')
        if not all([content_id, content_type]): return Response({"error": "content_id and content_type are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            model = apps.get_model('core', content_type.capitalize())
            model.objects.get(pk=content_id, author=request.user)
        except (LookupError, model.DoesNotExist): return Response({"error": "Invalid content_type or content not found/not owned by user."}, status=status.HTTP_404_NOT_FOUND)
        ext_request, created = ContentExtensionRequest.objects.get_or_create(content_id=content_id, user=request.user, defaults={'content_type': content_type})
        if not created and ext_request.status in ['pending', 'approved']: return Response({"status": "An extension request is already pending or has been approved."}, status=status.HTTP_200_OK)
        ext_request.status = 'pending'; ext_request.save()
        return Response(ContentExtensionRequestSerializer(ext_request).data, status=status.HTTP_201_CREATED)

class ReviewContentExtensionView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, pk, *args, **kwargs):
        try: ext_request = ContentExtensionRequest.objects.get(pk=pk, status='pending')
        except ContentExtensionRequest.DoesNotExist: return Response({"error": "Request not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action not in ['approve', 'deny']: return Response({"error": "Action must be 'approve' or 'deny'."}, status=status.HTTP_400_BAD_REQUEST)
        ext_request.status = f"{action}d"; ext_request.reviewed_by = request.user; ext_request.reviewed_at = timezone.now()
        if action == 'approve':
            try:
                model = apps.get_model('core', ext_request.content_type.capitalize())
                content_obj = model.objects.get(pk=ext_request.content_id)
                content_obj.expires_at += timedelta(days=30); content_obj.save()
            except (LookupError, model.DoesNotExist):
                ext_request.status = 'denied'; logger.error(f"Could not find content {ext_request.content_id} to approve extension.")
        ext_request.save()
        return Response(ContentExtensionRequestSerializer(ext_request).data, status=status.HTTP_200_OK)

class UnpinContentView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, *args, **kwargs):
        content_id, content_type = request.data.get('content_id'), request.data.get('content_type')
        if not all([content_id, content_type]): return Response({"error": "content_id and content_type are required."}, status=status.HTTP_400_BAD_REQUEST)
        try: model = apps.get_model('core', content_type.capitalize()); content_obj = model.objects.get(pk=content_id)
        except (LookupError, model.DoesNotExist): return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)
        if content_obj.pinned_by and content_obj.pinned_by.is_staff and not request.user.is_staff: return Response({"error": "Moderators cannot unpin content pinned by an Admin."}, status=status.HTTP_403_FORBIDDEN)
        content_obj.is_pinned = False; content_obj.pinned_by = None; content_obj.save()
        return Response({"status": "Content unpinned successfully."}, status=status.HTTP_200_OK)

# --- BitSync Protocol Views ---
@method_decorator(csrf_exempt, name='dispatch')
class SyncView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, *args, **kwargs):
        since_str = request.query_params.get('since')
        if not since_str:
            return Response({"error": "'since' timestamp is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            since_dt = timezone.datetime.fromisoformat(since_str.replace(' ', '+'))
            new_messages = Message.objects.filter(created_at__gt=since_dt, manifest__isnull=False)
            manifests = [msg.manifest for msg in new_messages]
            return JsonResponse({"manifests": manifests}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during sync operation: {e}", exc_info=True)
            return Response({"error": "Failed to process sync request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class BitSyncHasContentView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, *args, **kwargs):
        has_content = Message.objects.filter(manifest__content_hash=content_hash).exists() or \
                      FileAttachment.objects.filter(manifest__content_hash=content_hash).exists()
        return Response(status=status.HTTP_200_OK if has_content else status.HTTP_404_NOT_FOUND)

@method_decorator(csrf_exempt, name='dispatch')
class BitSyncChunkView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, chunk_index, *args, **kwargs):
        if not service_manager.bitsync_service:
            return Response({"error": "BitSync service not available"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, chunk_index)
        if chunk_path:
            try:
                with open(chunk_path, 'rb') as f:
                    return HttpResponse(f.read(), content_type='application/octet-stream')
            except IOError:
                raise Http404("Chunk file not readable or found on disk.")
        else:
            raise Http404("Chunk not found.")

