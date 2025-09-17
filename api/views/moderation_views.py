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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/api/views/moderation_views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.http import HttpResponse, Http404
from core.services.service_manager import service_manager
from django.utils import timezone
from datetime import timedelta
from django.apps import apps
import logging
# --- MODIFICATION START ---
import os
import base64
from django.conf import settings
# --- MODIFICATION END ---

from ..serializers import ContentExtensionRequestSerializer, ModerationReportSerializer, FederatedActionProfileUpdateSerializer
from ..permissions import IsModeratorOrAdmin
from core.models import IgnoredPubkey, BannedPubkey, FederatedAction, Message, ModerationReport, ContentExtensionRequest, FileAttachment, User

logger = logging.getLogger(__name__)


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
            reporter.save() # Save karma update
            
            message_to_delete = report.reported_message
            
            report.save()

            if message_to_delete and message_to_delete.manifest:
                FederatedAction.objects.create(
                    action_type='DELETE_CONTENT',
                    content_hash_target=message_to_delete.manifest.get('content_hash'),
                    action_details={'reason': f'Content removed by {request.user.username} based on user report: {report.comment}'}
                )
            
            if message_to_delete:
                message_to_delete.delete()
            
            return Response({"status": "Report approved and message deleted."})

        elif action == 'reject':
            report.status = 'rejected'
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            return Response({"status": "Report rejected."})

        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

class PendingProfileUpdatesQueueView(generics.ListAPIView):
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = FederatedActionProfileUpdateSerializer

    def get_queryset(self):
        return FederatedAction.objects.filter(
            action_type='update_profile',
            status='pending_approval'
        ).order_by('created_at')

class ReviewProfileUpdateView(views.APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, action_id, *args, **kwargs):
        action = request.data.get('action') # "approve" or "deny"
        try:
            profile_action = FederatedAction.objects.get(id=action_id, status='pending_approval', action_type='update_profile')
        except FederatedAction.DoesNotExist:
            return Response({"error": "Profile update request not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)

        # --- MODIFICATION START ---
        user = User.objects.get(pubkey=profile_action.pubkey_target)
        details = profile_action.action_details
        temp_filename = details.get('pending_avatar_filename')

        pending_dir = os.path.join(settings.MEDIA_ROOT, 'pending_avatars')
        source_path = os.path.join(pending_dir, temp_filename) if temp_filename else None

        if action == 'approve':
            final_avatar_path = None
            if source_path and os.path.exists(source_path):
                # This is an avatar update
                final_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
                os.makedirs(final_dir, exist_ok=True)
                
                final_filename = f"{user.username}_avatar.png"
                final_path = os.path.join(final_dir, final_filename)
                
                # Move the file from pending to final destination
                os.rename(source_path, final_path)
                
                # Update the user's profile to point to the new file
                user.avatar.name = os.path.join('avatars', final_filename)
                
                # Now, create the FileAttachment and manifest for federation
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
                        'content_type': 'image/png', 'size': len(image_bytes), 'manifest': manifest
                    }
                )
                details['avatar_hash'] = manifest.get('content_hash')

            # Update nickname regardless
            user.nickname = details.get('nickname', user.nickname)
            user.save()
            
            # Update the action for federation
            profile_action.status = 'approved'
            profile_action.action_details = details # Save the new avatar_hash
            profile_action.save()
            
            return Response({"status": "Profile update approved and will be federated."}, status=status.HTTP_200_OK)
            
        elif action == 'deny':
            # If the update is denied, delete the temporary file
            if source_path and os.path.exists(source_path):
                os.remove(source_path)
                
            profile_action.status = 'denied'
            profile_action.save()
            return Response({"status": "Profile update denied."}, status=status.HTTP_200_OK)
        # --- MODIFICATION END ---

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
        
        if content_obj.is_pinned and content_obj.manifest and content_obj.manifest.get('content_hash'):
             FederatedAction.objects.create(
                action_type='unpin_content',
                content_hash_target=content_obj.manifest.get('content_hash')
            )

        content_obj.is_pinned = False
        content_obj.pinned_by = None
        content_obj.save()
        return Response({"status": "Content unpinned successfully."}, status=status.HTTP_200_OK)
