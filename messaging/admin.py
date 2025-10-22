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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/messaging/admin.py
from django.contrib import admin
from django.contrib import messages as admin_messages
from .models import MessageBoard, Message, PrivateMessage
from federation.models import FederatedAction
import base64
import logging

logger = logging.getLogger(__name__)

@admin.action(description='Federate Delete (broadcasts delete to peers)')
def federate_delete_action(modeladmin, request, queryset):
    for item in queryset:
        if hasattr(item, 'metadata_manifest') and item.metadata_manifest:
            content_hash = item.metadata_manifest.get('content_hash')
            if content_hash:
                FederatedAction.objects.create(
                    action_type='DELETE_CONTENT',
                    content_hash_target=content_hash,
                    action_details={'reason': f'Content deleted by admin {request.user.username}'}
                )
    queryset.delete()

@admin.action(description='Rekey Message (creates new manifest for re-syncing)')
def rekey_message_action(modeladmin, request, queryset):
    """
    Re-encrypts selected messages with new BitSync manifests.
    This creates a new content_hash, making the message appear as "new" to peers.
    Useful for forcing messages to re-sync to federated peers.
    """
    from core.services.service_manager import service_manager

    if not service_manager.bitsync_service:
        from core.services.bitsync_service import BitSyncService
        service_manager.bitsync_service = BitSyncService()

    success_count = 0
    error_count = 0

    for message in queryset:
        try:
            # Build attachment hashes from the message's current attachments
            attachment_hashes = []
            if message.attachments.exists():
                attachment_hashes = [
                    att.metadata_manifest['content_hash']
                    for att in message.attachments.all()
                    if att.metadata_manifest
                ]

            # Create message content payload matching the standard format
            message_content_payload = {
                "type": "message",
                "subject": message.subject,
                "body": message.body,
                "board": message.board.name,
                "pubkey": message.pubkey,
                "attachment_hashes": attachment_hashes
            }

            # Create new BitSync manifest (re-encrypts with new keys)
            old_hash = message.metadata_manifest.get('content_hash', 'N/A')[:8] if message.metadata_manifest else 'none'
            content_hash, new_manifest = service_manager.bitsync_service.create_encrypted_content(message_content_payload)
            new_hash = content_hash[:8]

            # Update message with new manifest
            message.metadata_manifest = new_manifest
            message.save()

            success_count += 1
            logger.info(f"Rekeyed message '{message.subject}': {old_hash} → {new_hash}")
            admin_messages.success(
                request,
                f'Rekeyed "{message.subject}": {old_hash} → {new_hash}'
            )

        except Exception as e:
            error_count += 1
            admin_messages.error(
                request,
                f'Failed to rekey "{message.subject}": {str(e)}'
            )

    if success_count > 0:
        logger.info(f"Rekey operation completed: {success_count} message(s) rekeyed successfully. New manifests will sync to peers on next poll.")
        admin_messages.success(
            request,
            f'Successfully rekeyed {success_count} message(s). New manifests will sync to peers on next poll.'
        )
    if error_count > 0:
        logger.warning(f"Rekey operation had {error_count} failure(s).")
        admin_messages.warning(
            request,
            f'Failed to rekey {error_count} message(s).'
        )

class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'author', 'board', 'created_at')
    list_filter = ('board', 'author')
    actions = [federate_delete_action, rekey_message_action]

# Register your models here.
admin.site.register(MessageBoard)
admin.site.register(Message, MessageAdmin)
admin.site.register(PrivateMessage)
