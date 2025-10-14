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
            
            new_messages = Message.objects.filter(modified_at__gt=since_dt, metadata_manifest__isnull=False)
            new_files = FileAttachment.objects.filter(modified_at__gt=since_dt, metadata_manifest__isnull=False)
            new_pms = PrivateMessage.objects.filter(modified_at__gt=since_dt, metadata_manifest__isnull=False)
            new_applets = Applet.objects.filter(created_at__gt=since_dt, is_local=False, code_manifest__isnull=False)
            new_actions = FederatedAction.objects.filter(created_at__gt=since_dt, status='approved')

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

# ... (rest of the file is unchanged)
