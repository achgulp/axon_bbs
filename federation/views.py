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
#

# Full path: axon_bbs/federation/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.http import HttpResponse, Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
import os
import json
from datetime import timedelta
from django.apps import apps
import base64
from django.conf import settings
from django.db import IntegrityError
import uuid
from io import StringIO
from django.core import serializers
from django.core.management import call_command
from rest_framework.permissions import IsAdminUser

from .permissions import TrustedPeerPermission, IsModeratorOrAdmin
from .models import FederatedAction, ModerationReport, ContentExtensionRequest
from messaging.models import Message, PrivateMessage
from applets.models import Applet, AppletData
from accounts.models import IgnoredPubkey, BannedPubkey
from core.models import FileAttachment, User, TrustedInstance
from .serializers import ModerationReportSerializer, FederatedActionProfileUpdateSerializer, ContentExtensionRequestSerializer, ModerationInquirySerializer
from core.services.service_manager import service_manager
from accounts.avatar_generator import generate_cow_avatar
from core.services.encryption_utils import generate_short_id, encrypt_for_recipients_only, generate_checksum

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class SyncView(views.APIView):
    permission_classes = [TrustedPeerPermission]
    def get(self, request, *args, **kwargs):
        since_str = request.query_params.get('since')
        if not since_str: return Response({"error": "'since' timestamp is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            server_now = timezone.now()
            since_dt = timezone.datetime.fromisoformat(since_str.replace(' ', '+'))
            
            # --- MODIFICATION START ---
            # Changed all filters to use 'modified_at' instead of 'created_at'
            new_messages = Message.objects.filter(modified_at__gt=since_dt, metadata_manifest__isnull=False)
            new_files = FileAttachment.objects.filter(modified_at__gt=since_dt, metadata_manifest__isnull=False)
            new_pms = PrivateMessage.objects.filter(modified_at__gt=since_dt, metadata_manifest__isnull=False)
            # Applets do not have a modified_at field yet, so we still use created_at for them. This can be updated later if needed.
            new_applets = Applet.objects.filter(created_at__gt=since_dt, is_local=False, code_manifest__isnull=False)
            new_actions = FederatedAction.objects.filter(created_at__gt=since_dt, status='approved')
            # --- MODIFICATION END ---

            manifests = []
            all_items = list(new_messages) + list(new_files) + list(new_pms) + list(new_applets)

            # Get the requesting peer's public key from the permission class
            requesting_peer_pubkey = request.peer_instance.pubkey

            for item in all_items:
                if isinstance(item, Applet):
                    item_manifest = item.code_manifest
                    item_manifest['content_type'] = 'applet'
                else:
                    item_manifest = item.metadata_manifest

                if isinstance(item, Message):
                    item_manifest['content_type'] = 'message'
                elif isinstance(item, FileAttachment):
                    item_manifest['content_type'] = 'file'
                elif isinstance(item, PrivateMessage):
                    item_manifest['content_type'] = 'pm'

                # Perform a just-in-time rekey if necessary
                rekeyed_manifest = service_manager.bitsync_service.rekey_manifest_for_peer(
                    item_manifest,
                    requesting_peer_pubkey
                )
                manifests.append(rekeyed_manifest)

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
        has_content = Message.objects.filter(metadata_manifest__content_hash=content_hash).exists() or \
                      FileAttachment.objects.filter(metadata_manifest__content_hash=content_hash).exists() or \
                      PrivateMessage.objects.filter(metadata_manifest__content_hash=content_hash).exists() or \
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

        status_msg = f"Pubkey temporarily banned until {expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')}" if is_temporary else "Pubkey permanently banned."
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
                defaults={'comment': comment, 'report_type': 'message_report'}
            )

            if not created:
                return Response({"error": "You have already reported this message."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"status": "Message reported successfully."}, status=status.HTTP_201_CREATED)
        except Message.DoesNotExist:
            return Response({"error": "Message not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating report by user {request.user.username}: {e}")
            return Response({"error": "An error occurred while creating the report."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContactModeratorsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ModerationInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ModerationReport.objects.create(
            reporting_user=request.user,
            comment=serializer.validated_data['comment'],
            report_type='general_inquiry',
            status='pending'
        )
        return Response({"status": "Your inquiry has been sent to the moderators."}, status=status.HTTP_201_CREATED)

class UnifiedQueueView(views.APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request, *args, **kwargs):
        pending_reports = ModerationReport.objects.filter(status='pending')
        serialized_reports = []
        for report in pending_reports:
            data = ModerationReportSerializer(report, context={'request': request}).data
            data['ticket_type'] = report.report_type
            serialized_reports.append(data)

        pending_profile_updates = FederatedAction.objects.filter(
            action_type='update_profile',
            status='pending_approval'
        )
        serialized_profile_updates = []
        for update in pending_profile_updates:
            data = FederatedActionProfileUpdateSerializer(update, context={'request': request}).data
            data['ticket_type'] = 'profile_update'
            serialized_profile_updates.append(data)

        combined_queue = sorted(
            serialized_reports + serialized_profile_updates,
            key=lambda x: x['created_at'],
            reverse=True
        )
        
        return Response(combined_queue)

class ReviewReportView(views.APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, report_id, *args, **kwargs):
        action = request.data.get('action')
        try:
            report = ModerationReport.objects.get(id=report_id, status='pending')
        except ModerationReport.DoesNotExist:
            return Response({"error": "Report not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)

        moderator = request.user
        private_key = request.session.get('unencrypted_priv_key')

        if action == 'approve':
            report.status = 'approved'
            report.reviewed_by = moderator
            report.reviewed_at = timezone.now()
            
            reporter = report.reporting_user
            reporter.karma = reporter.karma + 5
            reporter.save()
            
            report.save()

            if report.report_type == 'general_inquiry':
                if not private_key:
                    return Response({"status": "Inquiry approved, but could not send PM acknowledgment: Moderator Identity is locked."}, status=status.HTTP_200_OK)

                recipient = report.reporting_user
                subject = "Regarding Your Recent Inquiry"
                body = f"Hello {recipient.nickname},\n\nThis is an automated message to confirm that a moderator has reviewed and closed your recent inquiry.\n\nOriginal inquiry:\n---\n{report.comment}\n---\n\nThank you for helping to keep the community running smoothly."
                
                e2e_payload = json.dumps({"subject": subject, "body": body, "sender_pubkey": moderator.pubkey, "recipient_pubkey": recipient.pubkey})
                e2e_encrypted_content, e2e_manifest = encrypt_for_recipients_only(e2e_payload, [moderator.pubkey, recipient.pubkey])
                metadata = {
                    "type": "pm",
                    "e2e_encrypted_content_b64": base64.b64encode(e2e_encrypted_content).decode('utf-8'),
                    "e2e_manifest": e2e_manifest,
                    "sender_pubkey": moderator.pubkey, "recipient_pubkey": recipient.pubkey,
                    "sender_pubkey_checksum": generate_checksum(moderator.pubkey),
                    "recipient_pubkey_checksum": generate_checksum(recipient.pubkey),
                }
                bbs_pubkeys = [inst.pubkey for inst in TrustedInstance.objects.all() if inst.pubkey]
                _content_hash, metadata_manifest = service_manager.bitsync_service.create_encrypted_content(metadata, b_b_s_instance_pubkeys=bbs_pubkeys)
                
                PrivateMessage.objects.create(
                    author=moderator, recipient=recipient, sender_pubkey=moderator.pubkey,
                    e2e_encrypted_content=base64.b64encode(e2e_encrypted_content).decode('utf-8'),
                    metadata_manifest=metadata_manifest
                )
                return Response({"status": "Inquiry marked as handled and acknowledgment PM sent."})

            else: 
                message_to_delete = report.reported_message
                if message_to_delete and message_to_delete.metadata_manifest:
                    FederatedAction.objects.create(
                        action_type='DELETE_CONTENT',
                        content_hash_target=message_to_delete.metadata_manifest.get('content_hash'),
                        action_details={'reason': f'Content removed by {moderator.username} based on user report: {report.comment}'}
                    )
                if message_to_delete:
                    message_to_delete.delete()
                
                return Response({"status": "Report approved and message deleted."})

        elif action == 'reject':
            report.status = 'rejected'
            report.reviewed_by = moderator
            report.reviewed_at = timezone.now()
            report.save()
            return Response({"status": "Report rejected."})

        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

class ReviewProfileUpdateView(views.APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, action_id, *args, **kwargs):
        action = request.data.get('action')
        try:
            profile_action = FederatedAction.objects.get(id=action_id, status='pending_approval', action_type='update_profile')
        except FederatedAction.DoesNotExist:
            return Response({"error": "Profile update request not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)

        short_id = generate_short_id(profile_action.pubkey_target, length=8)
        defaults = {
            'username': f"federated_{short_id}_{uuid.uuid4().hex[:4]}",
            'nickname': f"Moo-{short_id}",
            'is_active': False,
            'password': User.objects.make_random_password()
        }
        try:
            user, created = User.objects.get_or_create(pubkey=profile_action.pubkey_target, defaults=defaults)
            if created:
                logger.info(f"Created placeholder federated user '{user.username}' during moderation.")
                avatar_content_file, avatar_filename = generate_cow_avatar(user.pubkey)
                user.avatar.save(avatar_filename, avatar_content_file, save=True)
        except IntegrityError:
            user = User.objects.get(pubkey=profile_action.pubkey_target)
        
        details = profile_action.action_details
        temp_filename = details.get('pending_avatar_filename')

        pending_dir = os.path.join(settings.MEDIA_ROOT, 'pending_avatars')
        source_path = os.path.join(pending_dir, temp_filename) if temp_filename else None

        if action == 'approve':
            if source_path and os.path.exists(source_path):
                final_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
                os.makedirs(final_dir, exist_ok=True)
                
                final_filename = f"{user.username}_avatar.png"
                final_path = os.path.join(final_dir, final_filename)
                
                os.rename(source_path, final_path)
                
                user.avatar.name = os.path.join('avatars', final_filename)
                
                with open(final_path, 'rb') as f:
                    image_bytes = f.read()

                file_content = {
                    "type": "file", "filename": final_filename, "content_type": 'image/png',
                    "size": len(image_bytes), "data": base64.b64encode(image_bytes).decode('ascii')
                }
                _content_hash, manifest = service_manager.bitsync_service.create_encrypted_content(file_content)
                
                FileAttachment.objects.update_or_create(
                    author=user, filename=final_filename,
                    defaults={
                        'content_type': 'image/png', 
                        'size': len(image_bytes), 
                        'metadata_manifest': manifest
                    }
                )
                details['avatar_hash'] = manifest.get('content_hash')

            user.nickname = details.get('nickname', user.nickname)
            
            user.save()
            
            profile_action.status = 'approved'
            profile_action.action_details = details
            profile_action.save()
            
            return Response({"status": "Profile update approved and will be federated."}, status=status.HTTP_200_OK)
            
        elif action == 'deny':
            if source_path and os.path.exists(source_path):
                os.remove(source_path)
                
            profile_action.status = 'denied'
            profile_action.save()
            return Response({"status": "Profile update denied."}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid action. Must be 'approve' or 'deny'."}, status=status.HTTP_400_BAD_REQUEST)

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
        ext_request.status = 'pending'
        ext_request.save()
        return Response(ContentExtensionRequestSerializer(ext_request).data, status=status.HTTP_201_CREATED)

class ReviewContentExtensionView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, pk, *args, **kwargs):
        try: ext_request = ContentExtensionRequest.objects.get(pk=pk, status='pending')
        except ContentExtensionRequest.DoesNotExist: return Response({"error": "Request not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action not in ['approve', 'deny']: return Response({"error": "Action must be 'approve' or 'deny'."}, status=status.HTTP_400_BAD_REQUEST)
        ext_request.status = f"{action}d"
        ext_request.reviewed_by = request.user
        ext_request.reviewed_at = timezone.now()
        if action == 'approve':
            try:
                
                model = apps.get_model('core', ext_request.content_type.capitalize())
                content_obj = model.objects.get(pk=ext_request.content_id)
                content_obj.expires_at += timedelta(days=30)
                content_obj.save()
            except (LookupError, model.DoesNotExist):
                ext_request.status = 'denied'
 
                logger.error(f"Could not find content {ext_request.content_id} to approve extension.")
        ext_request.save()
        return Response(ContentExtensionRequestSerializer(ext_request).data, status=status.HTTP_200_OK)

class UnpinContentView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, *args, **kwargs):
        content_id, content_type = request.data.get('content_id'), request.data.get('content_type')
        if not all([content_id, content_type]): return Response({"error": "content_id and content_type are required."}, status=status.HTTP_400_BAD_REQUEST)
  
        try:
            model = apps.get_model('core', content_type.capitalize())
            content_obj = model.objects.get(pk=content_id)
        except (LookupError, model.DoesNotExist):
            return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)
        if content_obj.pinned_by and content_obj.pinned_by.is_staff and not request.user.is_staff: return Response({"error": "Moderators cannot unpin content pinned by an Admin."}, status=status.HTTP_403_FORBIDDEN)
 
        
        if content_obj.is_pinned and content_obj.metadata_manifest and content_obj.metadata_manifest.get('content_hash'):
             FederatedAction.objects.create(
                action_type='unpin_content',
                content_hash_target=content_obj.metadata_manifest.get('content_hash')
            )

        content_obj.is_pinned = False
 
        content_obj.pinned_by = None
        content_obj.save()
        return Response({"status": "Content unpinned successfully."}, status=status.HTTP_200_OK)

class ExportConfigView(views.APIView):
    permission_classes = [TrustedPeerPermission]

    def get(self, request, *args, **kwargs):
        try:
            output = StringIO()
            call_command(
         
        'dumpdata',
                'core.User', 'applets.Applet', 'applets.AppletCategory', 
                'messaging.MessageBoard', 'core.ValidFileType',
                stdout=output,
                exclude=['contenttypes', 'auth.permission']
            
 )
            return HttpResponse(output.getvalue(), content_type='application/json')
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return Response({"error": "Failed to generate configuration export."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
