# Full path: axon_bbs/api/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import logging
import json
import base64
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import IntegrityError
from cryptography.hazmat.primitives import serialization
from PIL import Image
from django.core.files.base import ContentFile
import io

from .serializers import UserSerializer, MessageBoardSerializer, MessageSerializer, ContentExtensionRequestSerializer, FileAttachmentSerializer, PrivateMessageSerializer, PrivateMessageOutboxSerializer, AppletSerializer
from .permissions import TrustedPeerPermission
from core.models import MessageBoard, Message, IgnoredPubkey, BannedPubkey, TrustedInstance, Alias, ContentExtensionRequest, FileAttachment, PrivateMessage, FederatedAction, Applet
from core.services.identity_service import IdentityService, DecryptionError
from core.services.encryption_utils import derive_key_from_password, generate_checksum, generate_short_id, encrypt_with_public_key, decrypt_with_private_key
from core.services.service_manager import service_manager
from core.services.content_validator import is_file_type_valid

logger = logging.getLogger(__name__)
User = get_user_model()

# ... (All views from RegisterView to FileDownloadView remain unchanged) ...
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
        except DecryptionError as e:
            logger.warning(f"Failed unlock attempt for {user.username}: {e}")
            return Response({"error": "Unlock failed. Please check your password."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Failed to unlock identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred during unlock."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ImportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        user = request.user
        account_password = request.data.get('account_password')
        key_file_password = request.data.get('key_file_password', None)
        private_key_pem = request.data.get('private_key')
        name = request.data.get('name', 'default')

        if 'key_file' in request.FILES:
            key_file = request.FILES['key_file']
            try:
                private_key_pem = key_file.read().decode('utf-8')
            except Exception as e:
                return Response({"error": f"Could not read the provided file: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        if not all([private_key_pem, account_password]):
            return Response({"error": "A private key and your current account password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            try:
                serialization.load_pem_private_key(
                    private_key_pem.strip().encode(),
                    password=key_file_password.encode() if key_file_password else None
                )
            except Exception as e:
                logger.warning(f"Invalid PEM format or wrong key password for user {user.username}: {e}")
                raise ValueError("Invalid private key format or incorrect key password.")

            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f: salt = f.read()
            encryption_key = derive_key_from_password(account_password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)

            existing_identity = identity_service.get_identity_by_name(name)
            if existing_identity:
                identity_service.remove_identity(existing_identity['id'])

            new_identity = identity_service.add_existing_identity(
                name,
                private_key_pem,
                password=key_file_password
            )

            if name == "default":
                user.pubkey = new_identity['public_key']
                user.save()

            return Response({"status": f"Identity '{name}' imported successfully."}, status=status.HTTP_201_CREATED)
        except DecryptionError as e:
            logger.warning(f"Failed import attempt for {user.username}: {e}")
            return Response({"error": "Failed to import identity. Please check your account password."}, status=status.HTTP_401_UNAUTHORIZED)
        except ValueError as e:
             logger.warning(f"Failed to import identity for {user.username}: {e}")
             return Response({"error": "Invalid private key format. Please ensure it is a valid PEM file and the key password is correct."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to import identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected server error occurred during import."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        password = request.data.get('password')
        name = request.data.get('name', 'default')

        if not password:
            return Response({"error": "Password is required to export and encrypt your key."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f: salt = f.read()
            encryption_key = derive_key_from_password(password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)
            identity = identity_service.get_identity_by_name(name)

            if not identity or 'private_key' not in identity:
                return Response({"error": f"Could not find the '{name}' identity."}, status=status.HTTP_404_NOT_FOUND)

            private_key_pem_from_storage = identity['private_key']

            try:
                key_object = serialization.load_pem_private_key(
                    private_key_pem_from_storage.strip().encode(),
                    password=None
                )
                encrypted_pem_output = key_object.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
                )
            except Exception as e:
                logger.error(f"FATAL: The stored private key for user {user.username} is corrupted and cannot be parsed: {e}")
                raise ValueError("The stored private key is corrupted and cannot be exported.")

            response = HttpResponse(encrypted_pem_output, content_type='application/x-pem-file')
            response['Content-Disposition'] = f'attachment; filename="{user.username}_axon_key_encrypted.pem"'
            return response
        except DecryptionError as e:
            logger.warning(f"Failed export attempt for {user.username}: {e}")
            return Response({"error": "Failed to export identity. Please check your password."}, status=status.HTTP_401_UNAUTHORIZED)
        except ValueError as e:
             return Response({"error": f"Could not export key: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Failed to import identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected server error occurred during export."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateNicknameView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        nickname = request.data.get('nickname')
        if not nickname:
            return Response({"error": "Nickname cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = request.user
            user.nickname = nickname
            user.save()
            return Response({"status": "Nickname updated successfully.", "nickname": nickname}, status=status.HTTP_200_OK)
        except IntegrityError:
            return Response({"error": "This nickname is already taken."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Could not update nickname for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "An error occurred while updating the nickname."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        return Response({
            "username": user.username,
            "nickname": user.nickname,
            "pubkey": user.pubkey,
            "avatar_url": user.avatar.url if user.avatar else None
        })

class UploadAvatarView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'avatar' not in request.FILES:
            return Response({"error": "No avatar file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['avatar']
        
        if file.size > 1024 * 1024:
            return Response({"error": "Avatar file size cannot exceed 1MB."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            img = Image.open(file)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.thumbnail((128, 128))
            
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='PNG')
            
            user = request.user
            user.avatar.save(f'{user.username}_avatar.png', ContentFile(thumb_io.getvalue()), save=True)
            
            user.save()

            return Response({"status": "Avatar updated.", "avatar_url": user.avatar.url})

        except Exception as e:
            logger.error(f"Could not process avatar for {request.user.username}: {e}")
            return Response({"error": "Invalid image file. Please upload a valid PNG, JPG, or GIF."}, status=status.HTTP_400_BAD_REQUEST)

class SendPrivateMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        identifier = request.data.get('recipient_identifier')
        pubkey = request.data.get('recipient_pubkey')
        subject = request.data.get('subject')
        body = request.data.get('body')
        sender = request.user

        if not all([identifier, subject, body]):
            return Response({"error": "Recipient identifier, subject, and body are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.session.get('unencrypted_priv_key') or not sender.pubkey:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)

        recipient_pubkey = None
        if pubkey:
            recipient_pubkey = pubkey
        else:
            local_user = User.objects.filter(username__iexact=identifier).first()
            alias = Alias.objects.filter(nickname__iexact=identifier).first()
            if local_user and local_user.pubkey:
                recipient_pubkey = local_user.pubkey
            elif alias and alias.pubkey:
                recipient_pubkey = alias.pubkey

        if not recipient_pubkey:
            return Response({"error": f"Recipient '{identifier}' not found or has no public key."}, status=status.HTTP_404_NOT_FOUND)

        if not service_manager.bitsync_service:
            return Response({"error": "BitSync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            is_new_contact = not Alias.objects.filter(pubkey=recipient_pubkey).exists()
            is_remote_user = not User.objects.filter(pubkey=recipient_pubkey).exists()

            if is_new_contact and is_remote_user:
                nickname_to_create = identifier
                if not Alias.objects.filter(nickname__iexact=nickname_to_create).exists():
                    Alias.objects.create(pubkey=recipient_pubkey, nickname=nickname_to_create)
                    logger.info(f"Created new alias '{nickname_to_create}' for first-time contact.")
                else:
                    logger.warning(f"Did not create alias for {recipient_pubkey[:12]} because nickname '{nickname_to_create}' already exists.")

            recipient_user = User.objects.filter(pubkey=recipient_pubkey).first()
            
            encrypted_for_recipient = encrypt_with_public_key(body, recipient_pubkey)
            encrypted_for_sender = encrypt_with_public_key(body, sender.pubkey)
            
            e2e_body = { "recipient_copy": encrypted_for_recipient, "sender_copy": encrypted_for_sender }

            pm_content = {
                "type": "pm",
                "sender_pubkey": sender.pubkey,
                "recipient_pubkey": recipient_pubkey,
                "subject": subject,
                "body": e2e_body
            }
            
            content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(pm_content)
            
            PrivateMessage.objects.create(
                author=sender,
                recipient=recipient_user,
                recipient_pubkey=recipient_pubkey,
                sender_pubkey=sender.pubkey,
                subject=subject,
                manifest=manifest
            )
            logger.info(f"User {sender.username} sent E2E encrypted PM to key starting with {recipient_pubkey[:12]}...")
            return Response({"status": "Message sent successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to send private message for {sender.username}: {e}", exc_info=True)
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
        user_privkey = request.session.get('unencrypted_priv_key')

        for pm in received_messages:
            try:
                decrypted_content_bytes = service_manager.sync_service.get_decrypted_content(pm.manifest)
                if decrypted_content_bytes:
                    content = json.loads(decrypted_content_bytes.decode('utf-8'))
                    e2e_body = content.get('body', {})
                    if isinstance(e2e_body, dict) and 'recipient_copy' in e2e_body:
                        pm.decrypted_body = decrypt_with_private_key(e2e_body['recipient_copy'], user_privkey)
                    else: 
                        pm.decrypted_body = str(e2e_body)
                else:
                    pm.decrypted_body = '[Content not available or still syncing]'
            except Exception as e:
                logger.error(f"Could not decrypt PM {pm.id} for user {request.user.username}: {e}")
                pm.decrypted_body = '[Decryption Error]'
            
            decrypted_messages.append(pm)
            
        serializer = PrivateMessageSerializer(decrypted_messages, many=True)
        return Response(serializer.data)

class PrivateMessageOutboxView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not service_manager.sync_service:
            return Response({"error": "Sync service is not available."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        sent_messages = PrivateMessage.objects.filter(author=request.user).order_by('-created_at')
        
        decrypted_messages = []
        user_privkey = request.session.get('unencrypted_priv_key')

        for pm in sent_messages:
            try:
                decrypted_content_bytes = service_manager.sync_service.get_decrypted_content(pm.manifest)
                if decrypted_content_bytes:
                    content = json.loads(decrypted_content_bytes.decode('utf-8'))
                    e2e_body = content.get('body', {})
                    if isinstance(e2e_body, dict) and 'sender_copy' in e2e_body:
                        pm.decrypted_body = decrypt_with_private_key(e2e_body['sender_copy'], user_privkey)
                    else: 
                        pm.decrypted_body = str(e2e_body)
                else:
                    pm.decrypted_body = '[Content not available]'
            except Exception as e:
                logger.error(f"Could not decrypt sent PM {pm.id} for user {request.user.username}: {e}")
                pm.decrypted_body = '[Decryption Error]'
            
            decrypted_messages.append(pm)
            
        serializer = PrivateMessageOutboxSerializer(decrypted_messages, many=True)
        return Response(serializer.data)

class FileUploadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        if not service_manager.bitsync_service:
            return Response({"error": "Sync service is unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            raw_data = uploaded_file.read()
            file_content = {
                "type": "file",
                "filename": uploaded_file.name,
                "content_type": uploaded_file.content_type,
                "size": uploaded_file.size,
                "data": base64.b64encode(raw_data).decode('ascii')
            }
            
            temp_hash_data = json.dumps(file_content, sort_keys=True).encode('utf-8')
            content_hash = hashlib.sha256(temp_hash_data).hexdigest()
            
            existing_attachment = FileAttachment.objects.filter(manifest__content_hash=content_hash).first()
            if existing_attachment:
                logger.info(f"Duplicate file upload for '{uploaded_file.name}'. Reusing existing attachment.")
                serializer = FileAttachmentSerializer(existing_attachment)
                return Response(serializer.data, status=status.HTTP_200_OK)

            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(file_content)

            attachment = FileAttachment.objects.create(
                author=request.user, filename=uploaded_file.name, content_type=uploaded_file.content_type,
                size=uploaded_file.size, manifest=manifest
            )
            serializer = FileAttachmentSerializer(attachment)
            logger.info(f"User {request.user.username} uploaded new file '{attachment.filename}' ({attachment.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Failed to process file upload for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "Server error during file processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileDownloadView(views.APIView):
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
            
            content = json.loads(decrypted_data)
            file_bytes = base64.b64decode(content['data'])

            if not is_file_type_valid(file_bytes):
                logger.warning(f"Blocked download of file '{attachment.filename}' ({attachment.id}) due to invalid file type.")
                return Response({"error": "This file type is not permitted on the server."}, status=status.HTTP_403_FORBIDDEN)

            response = HttpResponse(file_bytes, content_type=attachment.content_type)
            response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
            return response
        except Exception as e:
            logger.error(f"Error during file download for file {file_id}: {e}", exc_info=True)
            return Response({"error": "An error occurred while preparing the file for download."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DownloadContentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, content_hash, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not service_manager.sync_service:
            return Response({"error": "Sync service is not available."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        manifest = None
        models_to_check = [Message, FileAttachment, PrivateMessage, Applet]
        for model in models_to_check:
            manifest_field_name = 'code_manifest' if model is Applet else 'manifest'
            filter_kwargs = {f'{manifest_field_name}__content_hash': content_hash}
            
            item = model.objects.filter(**filter_kwargs).first()
            if item:
                manifest = getattr(item, manifest_field_name)
                break
        
        if not manifest:
            raise Http404("Content with the specified hash not found.")

        try:
            decrypted_data = service_manager.sync_service.get_decrypted_content(manifest)
            if decrypted_data is None:
                return Response({"error": "Failed to retrieve or decrypt content from the network."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # UPDATED: Log the successful download for debugging
            logger.info(f"User '{request.user.username}' successfully decrypted and downloaded content with hash: {content_hash[:12]}...")

            content_details = json.loads(decrypted_data.decode('utf-8'))
            applet_code = content_details.get('code', '')
            
            return HttpResponse(applet_code, content_type='application/javascript')
        except Exception as e:
            logger.error(f"Error during generic content download for hash {content_hash}: {e}", exc_info=True)
            return Response({"error": "An error occurred while preparing content for download."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id, *args, **kwargs):
        try:
            attachment = FileAttachment.objects.get(id=file_id)
            if service_manager.bitsync_service.are_all_chunks_local(attachment.manifest):
                return JsonResponse({"status": "available"})
            else:
                return JsonResponse({"status": "syncing"})
        except FileAttachment.DoesNotExist:
            raise Http404("File not found.")
        except Exception as e:
            logger.error(f"Error checking status for file {file_id}: {e}", exc_info=True)
            return Response({"error": "Could not determine file status."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        user, subject, body = request.user, request.data.get('subject'), request.data.get('body')
        board_name, attachment_ids = request.data.get('board_name', 'general'), request.data.get('attachment_ids', [])
        
        if not all([subject, body]):
            return Response({"error": "Subject and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            board, _ = MessageBoard.objects.get_or_create(name=board_name)
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
        
        action_details = {'is_temporary': is_temporary}
        if is_temporary:
            action_details['duration_hours'] = duration_hours
            
        action = FederatedAction.objects.create(
            action_type='ban_pubkey',
            pubkey_target=pubkey,
            action_details=action_details
        )
        
        BannedPubkey.objects.update_or_create(
            pubkey=pubkey, 
            defaults={'is_temporary': is_temporary, 'expires_at': expires_at, 'federated_action_id': action.id}
        )

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
        
        if content_obj.is_pinned and content_obj.manifest and content_obj.manifest.get('content_hash'):
             FederatedAction.objects.create(
                action_type='unpin_content',
                content_hash_target=content_obj.manifest.get('content_hash')
            )

        content_obj.is_pinned = False; content_obj.pinned_by = None; content_obj.save()
        return Response({"status": "Content unpinned successfully."}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class SyncView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, *args, **kwargs):
        since_str = request.query_params.get('since')
        if not since_str: return Response({"error": "'since' timestamp is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            server_now = timezone.now()
            since_dt = timezone.datetime.fromisoformat(since_str.replace(' ', '+'))
            
            new_messages = Message.objects.filter(created_at__gt=since_dt, manifest__isnull=False)
            new_files = FileAttachment.objects.filter(created_at__gt=since_dt, manifest__isnull=False)
            new_pms = PrivateMessage.objects.filter(created_at__gt=since_dt, manifest__isnull=False)
            new_applets = Applet.objects.filter(created_at__gt=since_dt, is_local=False, code_manifest__isnull=False)
            new_actions = FederatedAction.objects.filter(created_at__gt=since_dt)

            manifests = []
            all_items = list(new_messages) + list(new_files) + list(new_pms) + list(new_applets)

            for item in all_items:
                if isinstance(item, Applet):
                    item_manifest = item.code_manifest
                    item_manifest['content_type'] = 'applet'
                else:
                    item_manifest = item.manifest
                
                if isinstance(item, Message):
                    item_manifest['content_type'] = 'message'
                elif isinstance(item, FileAttachment):
                    item_manifest['content_type'] = 'file'
                    item_manifest['filename'] = item.filename
                    item_manifest['content_type_val'] = item.content_type
                    item_manifest['size'] = item.size
                elif isinstance(item, PrivateMessage):
                    item_manifest['content_type'] = 'pm'
                
                manifests.append(item_manifest)

            actions_payload = [
                {
                    "id": str(action.id),
                    "action_type": action.action_type,
                    "pubkey_target": action.pubkey_target,
                    "content_hash_target": action.content_hash_target,
                    "action_details": action.action_details,
                    "created_at": action.created_at.isoformat(),
                } for action in new_actions
            ]

            return JsonResponse({
                "manifests": manifests,
                "federated_actions": actions_payload,
                "server_timestamp": server_now.isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error during sync operation: {e}", exc_info=True)
            return Response({"error": "Failed to process sync request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class BitSyncHasContentView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, *args, **kwargs):
        has_content = Message.objects.filter(manifest__content_hash=content_hash).exists() or \
                      FileAttachment.objects.filter(manifest__content_hash=content_hash).exists() or \
                      PrivateMessage.objects.filter(manifest__content_hash=content_hash).exists() or \
                      Applet.objects.filter(code_manifest__content_hash=content_hash).exists()
        return Response(status=status.HTTP_200_OK if has_content else status.HTTP_404_NOT_FOUND)

@method_decorator(csrf_exempt, name='dispatch')
class BitSyncChunkView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, content_hash, chunk_index, *args, **kwargs):
        if not service_manager.bitsync_service: return Response({"error": "BitSync service not available"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, chunk_index)
        if chunk_path and os.path.exists(chunk_path):
            try:
                with open(chunk_path, 'rb') as f:
                    return HttpResponse(f.read(), content_type='application/octet-stream')
            except IOError: raise Http404("Chunk file not readable.")
        else: raise Http404("Chunk not found.")

class GetPublicKeyView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            local_instance = TrustedInstance.objects.get(
                encrypted_private_key__isnull=False,
                is_trusted_peer=False
            )
            if local_instance.pubkey:
                return JsonResponse({"public_key": local_instance.pubkey})
            else:
                return Response({"error": "Local instance has no public key."}, status=status.HTTP_404_NOT_FOUND)
        except TrustedInstance.DoesNotExist:
            return Response({"error": "Local instance not configured."}, status=status.HTTP_404_NOT_FOUND)
        except TrustedInstance.MultipleObjectsReturned:
            return Response({"error": "Configuration error: Multiple local instances found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppletListView(generics.ListAPIView):
    queryset = Applet.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppletSerializer
