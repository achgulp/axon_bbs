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


# Full path: axon_bbs/api/views/federation_views.py
from rest_framework import status, views
from rest_framework.response import Response
from django.http import HttpResponse, Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
import os

from ..permissions import TrustedPeerPermission
from core.models import Message, FileAttachment, PrivateMessage, Applet, FederatedAction, AppletData
from core.services.service_manager import service_manager

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
