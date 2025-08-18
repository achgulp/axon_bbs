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

from .serializers import UserSerializer, MessageBoardSerializer, MessageSerializer, ContentExtensionRequestSerializer, FileAttachmentSerializer, PrivateMessageSerializer
from .permissions import TrustedPeerPermission
from core.models import MessageBoard, Message, IgnoredPubkey, BannedPubkey, TrustedInstance, Alias, ContentExtensionRequest, FileAttachment, PrivateMessage
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_checksum, generate_short_id
from core.services.service_manager import service_manager
from core.services.content_validator import is_file_type_valid

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

class ImportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

# --- Private Messaging Views (UPDATED for Federation) ---
class SendPrivateMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        identifier = request.data.get('recipient_identifier')
        pubkey = request.data.get('recipient_pubkey') # Can be null on subsequent sends
        subject = request.data.get('subject')
        body = request.data.get('body')

        if not all([identifier, subject, body]):
            return Response({"error": "Recipient identifier, subject, and body are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)

        # --- Resolve Identifier to Public Key ---
        recipient_pubkey = None
        if pubkey:
            recipient_pubkey = pubkey
        else:
            local_user = User.objects.filter(username=identifier).first()
            alias = Alias.objects.filter(nickname=identifier).first()
            if local_user and local_user.pubkey:
                recipient_pubkey = local_user.pubkey
            elif alias and alias.pubkey:
                recipient_pubkey = alias.pubkey

        if not recipient_pubkey:
            return Response({"error": f"Recipient '{identifier}' not found or has no public key."}, status=status.HTTP_404_NOT_FOUND)

        if not service_manager.bitsync_service:
            return Response({"error": "BitSync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            # --- Auto-create Alias on first contact ---
            is_new_contact = not Alias.objects.filter(pubkey=recipient_pubkey).exists()
            is_remote_user = not User.objects.filter(pubkey=recipient_pubkey).exists()

            if is_new_contact and is_remote_user:
                # The identifier from the frontend (e.g., "Moo-12345678") is the desired nickname
                nickname_to_create = identifier
                if not Alias.objects.filter(nickname=nickname_to_create).exists():
                    Alias.objects.create(pubkey=recipient_pubkey, nickname=nickname_to_create)
                    logger.info(f"Created new alias '{nickname_to_create}' for first-time contact.")
                else:
                    logger.warning(f"Did not create alias for {recipient_pubkey[:12]} because nickname '{nickname_to_create}' already exists.")

            recipient_user = User.objects.filter(pubkey=recipient_pubkey).first()
            message_content = {"subject": subject, "body": body}
            raw_data = json.dumps(message_content).encode('utf-8')
            manifest = service_manager.bitsync_service.create_manifest_and_store_chunks(
                raw_data, recipients_pubkeys=[recipient_pubkey]
            )
            PrivateMessage.objects.create(
                author=request.user,
                recipient=recipient_user,
                recipient_pubkey=recipient_pubkey,
                subject=subject,
                manifest=manifest
            )
            logger.info(f"User {request.user.username} sent PM to key starting with {recipient_pubkey[:12]}...")
            return Response({"status": "Message sent successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to send private message for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "Server error while sending message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PrivateMessageListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not service_manager.sync_service:
            return Response({"error": "Sync service is not available."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        user_pubkey = request.user.pubkey
        if not user_pubkey:
            return Response({"error": "Current user does not have a public key."}, status=status.HTTP_400_BAD_REQUEST)
            
        received_messages = PrivateMessage.objects.filter(recipient_pubkey=user_pubkey).order_by('-created_at')
        
        decrypted_messages = []
        for pm in received_messages:
            try:
                decrypted_content_bytes = service_manager.sync_service.get_decrypted_content(pm.manifest)
                if decrypted_content_bytes:
                    content = json.loads(decrypted_content_bytes.decode('utf-8'))
                    pm.decrypted_body = content.get('body', '[Decryption Failed]')
                else:
                    pm.decrypted_body = '[Content not available or still syncing]'
            except Exception as e:
                logger.error(f"Could not decrypt PM {pm.id} for user {request.user.username}: {e}")
                pm.decrypted_body = '[Decryption Error]'
            
            decrypted_messages.append(pm)
            
        serializer = PrivateMessageSerializer(decrypted_messages, many=True)
        return Response(serializer.data)


# --- File Handling Views ---
# ... (rest of the file is unchanged)
