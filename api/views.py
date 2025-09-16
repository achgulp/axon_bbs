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

from .serializers import UserSerializer, MessageBoardSerializer, MessageSerializer, ContentExtensionRequestSerializer, FileAttachmentSerializer, PrivateMessageSerializer, PrivateMessageOutboxSerializer, AppletSerializer, HighScoreSerializer, ModerationReportSerializer
from .permissions import TrustedPeerPermission, IsModeratorOrAdmin
from core.models import MessageBoard, Message, IgnoredPubkey, BannedPubkey, TrustedInstance, Alias, ContentExtensionRequest, FileAttachment, PrivateMessage, FederatedAction, Applet, AppletData, HighScore, AppletSharedState, ModerationReport
from core.services.identity_service import IdentityService, DecryptionError
from core.services.encryption_utils import derive_key_from_password, generate_checksum, generate_short_id, encrypt_with_public_key, decrypt_with_private_key
from core.services.service_manager import service_manager
from core.services.content_validator import is_file_type_valid

logger = logging.getLogger(__name__)
User = get_user_model()


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
            identity_service = IdentityService(user=user)
            private_key = identity_service.get_unlocked_private_key(password)
            if not private_key:
                raise DecryptionError("Failed to unlock with provided password.")
            
            request.session['unencrypted_priv_key'] = private_key
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
        return Response({"error": "Import functionality is not yet updated for the new identity system."}, status=status.HTTP_501_NOT_IMPLEMENTED)

class ExportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response({"error": "Export functionality is not yet updated for the new identity system."}, status=status.HTTP_501_NOT_IMPLEMENTED)

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

            avatar_attachment = FileAttachment.objects.filter(author=user, filename=f'{user.username}_avatar.png').first()

            FederatedAction.objects.create(
                action_type='update_profile',
                pubkey_target=user.pubkey,
                status='pending_approval',
                action_details={
                    'nickname': user.nickname,
                    'karma': user.karma,
                    'avatar_hash': avatar_attachment.manifest.get('content_hash') if avatar_attachment else None
                }
            )
            return Response({"status": "Nickname update submitted for approval.", "nickname": nickname}, status=status.HTTP_200_OK)
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
            "avatar_url": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "karma": user.karma,
            "is_moderator": user.is_moderator,
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
            
            file_content = {
                "type": "file", "filename": f'{user.username}_avatar.png', "content_type": 'image/png',
                "size": thumb_io.tell(), "data": base64.b64encode(thumb_io.getvalue()).decode('ascii')
            }
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(file_content)
            
            FileAttachment.objects.update_or_create(
                author=user,
                filename=f'{user.username}_avatar.png',
                defaults={
                    'content_type': 'image/png',
                    'size': thumb_io.tell(),
                    'manifest': manifest
                }
            )

            user.avatar.save(f'{user.username}_avatar.png', ContentFile(thumb_io.getvalue()), save=True)
            user.save()

            FederatedAction.objects.create(
                action_type='update_profile',
                pubkey_target=user.pubkey,
                status='pending_approval',
                action_details={
                    'nickname': user.nickname,
                    'karma': user.karma,
                    'avatar_hash': manifest.get('content_hash')
                }
            )

            return Response({"status": "Avatar update submitted for approval.", "avatar_url": user.avatar.url})

        except Exception as e:
            logger.error(f"Could not process avatar for {request.user.username}: {e}")
            return Response({"error": "Invalid image file. Please upload a valid PNG, JPG, or GIF."}, status=status.HTTP_400_BAD_REQUEST)

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

class ReportMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        message_id = request.data.get('message_id')
        comment = request.data.get('comment', '')
        
        try:
            message_to_report = Message.objects.get(id=message_id)
            if message_to_report.author == request.user:
                return Response({"error": "You cannot report your own messages."}, status=status.HTTP_400_BAD_REQUEST)
            
            report, created = ModerationReport.objects.get_or_create(
                reported_message=message_to_report,
                reporting_user=request.user,
                defaults={'comment': comment}
            )

            if not created:
                return Response({"error": "You have already reported this message."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"status": "Message reported successfully."}, status=status.HTTP_201_CREATED)
        except Message.DoesNotExist:
            return Response({"error": "Message not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating report by user {request.user.username}: {e}")
            return Response({"error": "An error occurred while creating the report."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModeratorQueueView(generics.ListAPIView):
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = ModerationReportSerializer
    queryset = ModerationReport.objects.filter(status='pending').order_by('created_at')

class ReviewReportView(views.APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, report_id, *args, **kwargs):
        action = request.data.get('action') # "approve" or "reject"
        try:
            report = ModerationReport.objects.get(id=report_id, status='pending')
        except ModerationReport.DoesNotExist:
            return Response({"error": "Report not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            report.status = 'approved'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            
            reporter = report.reporting_user
            reporter.karma = reporter.karma + 5
            reporter.save()
            
            message_to_delete = report.reported_message
            if message_to_delete.manifest:
                FederatedAction.objects.create(
                    action_type='DELETE_CONTENT',
                    content_hash_target=message_to_delete.manifest.get('content_hash'),
                    action_details={'reason': f'Content removed by {request.user.username} based on user report: {report.comment}'}
                )
            
            message_to_delete.delete()
            report.save()
            return Response({"status": "Report approved and message deleted."})

        elif action == 'reject':
            report.status = 'rejected'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            return Response({"status": "Report rejected."})

        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

class GetSecurityQuestionsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
            identity_service = IdentityService(user=user)
            questions = identity_service.get_security_questions()
            if questions:
                return Response(questions)
            else:
                return Response({"error": "User does not have manifest-based recovery configured."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class SubmitRecoveryView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        answer_1 = request.data.get('answer_1')
        answer_2 = request.data.get('answer_2')
        new_password = request.data.get('new_password')

        if not all([username, answer_1, answer_2, new_password]):
            return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
            identity_service = IdentityService(user=user)
            
            success = identity_service.recover_identity_with_answers(answer_1, answer_2, new_password)
            
            if success:
                user.set_password(new_password)
                user.save()
                return Response({"status": "Password has been successfully reset."})
            else:
                return Response({"error": "Recovery failed. One or more answers were incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

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
            new_actions = FederatedAction.objects.filter(created_at__gt=since_dt, status='approved')

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
                      Applet.objects.filter(code_manifest__content_hash=content_hash).exists() or \
                      AppletData.objects.filter(data_manifest__content_hash=content_hash).exists()
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

class GetSaveAppletDataView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, applet_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            applet_data = AppletData.objects.get(applet_id=applet_id, owner=request.user)
            decrypted_bytes = service_manager.sync_service.get_decrypted_content(applet_data.data_manifest)
            if decrypted_bytes:
                content = json.loads(decrypted_bytes.decode('utf-8'))
                return Response(content.get('data'))
            else:
                return Response(None, status=status.HTTP_204_NO_CONTENT)
        except AppletData.DoesNotExist:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error getting applet data for {request.user.username} and applet {applet_id}: {e}")
            return Response({"error": "Could not retrieve applet data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, applet_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            applet = Applet.objects.get(id=applet_id)
            user = request.user
            new_data = request.data

            content_to_encrypt = {
                "type": "applet_data",
                "applet_id": str(applet.id),
                "owner_pubkey": user.pubkey,
                "data": new_data
            }
            
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(
                content_to_encrypt,
                recipients_pubkeys=[user.pubkey]
            )

            AppletData.objects.update_or_create(
                applet=applet,
                owner=user,
                defaults={'data_manifest': manifest}
            )
            logger.info(f"User {user.username} saved data for applet '{applet.name}'.")
            return Response({"status": "data saved successfully"}, status=status.HTTP_200_OK)
        except Applet.DoesNotExist:
            return Response({"error": "Applet not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error saving applet data for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred while saving data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HighScoreListView(generics.ListAPIView):
    serializer_class = HighScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        applet_id = self.kwargs.get('applet_id')
        return HighScore.objects.filter(applet_id=applet_id).order_by('-score')[:25]

class PostAppletEventView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, applet_id, *args, **kwargs):
        if not request.session.get('unencrypted_priv_key'):
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            applet = Applet.objects.get(id=applet_id)
            if not applet.event_board:
                return Response({"error": "This applet does not have an event board configured."}, status=status.HTTP_400_BAD_REQUEST)
            
            user = request.user
            subject = request.data.get('subject')
            body = request.data.get('body')
            
            message_content = { "type": "message", "subject": subject, "body": body, "board": applet.event_board.name, "pubkey": user.pubkey }
            _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(message_content)
            
            Message.objects.create(
                board=applet.event_board, 
                subject=subject, 
                body=body, 
                author=user, 
                pubkey=user.pubkey, 
                manifest=manifest,
                agent_status='pending'
            )
            return Response({"status": "event posted successfully"}, status=status.HTTP_201_CREATED)
        except Applet.DoesNotExist:
            return Response({"error": "Applet not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error posting applet event for {request.user.username}: {e}", exc_info=True)
            return Response({"error": "Server error while posting event."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReadAppletEventsView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        applet_id = self.kwargs.get('applet_id')
        try:
            applet = Applet.objects.get(id=applet_id)
            if applet.event_board:
                return Message.objects.filter(board=applet.event_board).order_by('-created_at')[:50]
        except Applet.DoesNotExist:
            return Message.objects.none()
        return Message.objects.none()

class AppletSharedStateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, applet_id, *args, **kwargs):
        try:
            shared_state = AppletSharedState.objects.get(applet_id=applet_id)
            return Response({
                "applet_id": shared_state.applet_id,
                "version": shared_state.version,
                "state_data": shared_state.state_data,
                "last_updated": shared_state.last_updated
            })
        except AppletSharedState.DoesNotExist:
            raise Http404

class AppletStateVersionView(views.APIView):
    permission_classes = [TrustedPeerPermission]

    def get(self, request, applet_id, *args, **kwargs):
        try:
            shared_state = AppletSharedState.objects.get(applet_id=applet_id)
            return JsonResponse({"version": shared_state.version})
        except AppletSharedState.DoesNotExist:
            raise Http404
