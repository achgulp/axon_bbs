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


# Full path: axon_bbs/core/admin.py
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from .models import User, TrustedInstance, FileAttachment, ValidFileType, SharedLibrary
from federation.models import FederatedAction
from core.services.service_manager import service_manager
import requests
from django.core.management import call_command
from io import StringIO
import json
import sys

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Axon BBS Fields', {
            'fields': ('access_level', 'is_banned', 'pubkey', 'nickname', 'avatar', 'is_agent', 'agent_service_path', 'agent_parameters', 'is_moderator', 'karma', 'last_moderated_at', 'timezone'),
        }),
    )
    list_display = ('username', 'nickname', 'is_staff', 'is_moderator', 'is_agent')

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

@admin.register(TrustedInstance)
class TrustedInstanceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_trusted_peer', 'last_synced_at')
    actions = ['fetch_public_key', 'force_refresh_and_rekey', 'clone_config_from_peer', 'clone_full_bbs']

    def fetch_public_key(self, request, queryset):
        for instance in queryset.filter(is_trusted_peer=True):
            url = instance.web_ui_onion_url
            if url:
                try:
                    call_command('update_peer_key', url)
                    self.message_user(request, f"Successfully updated public key for {url}.", messages.SUCCESS)
                except Exception as e:
                    self.message_user(request, f"Failed to update key for {url}: {e}", messages.ERROR)
    fetch_public_key.short_description = "Fetch public key from peer"

    def force_refresh_and_rekey(self, request, queryset):
        sync_service = service_manager.sync_service
        if not sync_service or not sync_service.private_key:
            self.message_user(request, "Sync service not initialized. Cannot perform re-key.", messages.ERROR)
            return

        for instance in queryset.filter(is_trusted_peer=True):
            instance.pubkey = None
            instance.save()
            
            self.fetch_public_key(request, TrustedInstance.objects.filter(pk=instance.pk))
            instance.refresh_from_db()

            if instance.pubkey:
                from messaging.models import Message, PrivateMessage
                from core.models import FileAttachment
                from applets.models import Applet
                import logging
                logger = logging.getLogger(__name__)

                # Re-key all content types
                messages_updated = 0
                files_updated = 0
                pms_updated = 0
                applets_updated = 0

                for message in Message.objects.all():
                    if message.metadata_manifest:
                        try:
                            message.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(message.metadata_manifest)
                            message.save()
                            messages_updated += 1
                        except Exception as e:
                            logger.error(f"Failed to rekey message {message.id}: {e}")

                for file_obj in FileAttachment.objects.all():
                    if file_obj.metadata_manifest:
                        try:
                            file_obj.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(file_obj.metadata_manifest)
                            file_obj.save()
                            files_updated += 1
                        except Exception as e:
                            logger.error(f"Failed to rekey file {file_obj.id}: {e}")

                for pm in PrivateMessage.objects.all():
                    if pm.metadata_manifest:
                        try:
                            pm.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(pm.metadata_manifest)
                            pm.save()
                            pms_updated += 1
                        except Exception as e:
                            logger.error(f"Failed to rekey PM {pm.id}: {e}")

                for applet in Applet.objects.all():
                    if applet.code_manifest:
                        try:
                            applet.code_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(applet.code_manifest)
                            applet.save()
                            applets_updated += 1
                        except Exception as e:
                            logger.error(f"Failed to rekey applet {applet.id}: {e}")

                self.message_user(request, f"Forced refresh and re-keyed all content for {instance.web_ui_onion_url}. Updated: {messages_updated} messages, {files_updated} files, {pms_updated} PMs, {applets_updated} applets.", messages.SUCCESS)
    force_refresh_and_rekey.short_description = "Force Refresh and Re-key Peer"

    def clone_config_from_peer(self, request, queryset):
        """Clone configuration only (no applets). For full clone including applets, use clone_full_bbs."""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one peer to clone from.", messages.ERROR)
            return

        peer = queryset.first()
        sync_service = service_manager.sync_service
        if not sync_service or not sync_service.private_key:
            self.message_user(request, "Sync service not initialized.", messages.ERROR)
            return

        target_url = f"{peer.web_ui_onion_url.strip('/')}/api/federation/export_config/"
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        try:
            headers = sync_service._get_auth_headers()
            response = requests.get(target_url, headers=headers, proxies=proxies, timeout=120)
            if response.status_code != 200:
                raise Exception(f"Peer returned status {response.status_code}")

            data = response.json()

            # Step 1: Find all superuser primary keys from the peer data
            superuser_pks = {
                obj['pk'] for obj in data
                if obj['model'] == 'core.user' and obj['fields'].get('is_superuser')
            }

            # Step 2: Filter out superusers AND any objects that link to them
            filtered_objects = []
            for obj in data:
                # Condition A: Skip if the object itself is a superuser
                if obj['model'] == 'core.user' and obj['pk'] in superuser_pks:
                    continue

                # Condition B: Skip if the object has a foreign key to a superuser
                fields = obj.get('fields', {})
                owner_pk = fields.get('owner')      # Used in Applet
                user_pk = fields.get('user')        # Used in IgnoredPubkey
                author_pk = fields.get('author')    # Used in Message, FileAttachment

                if (owner_pk in superuser_pks or
                    user_pk in superuser_pks or
                    author_pk in superuser_pks):
                    continue

                filtered_objects.append(obj)

            # Temporarily redirect stdin to feed the data to the loaddata command
            old_stdin = sys.stdin
            sys.stdin = StringIO(json.dumps(filtered_objects))
            try:
                call_command('loaddata', '-', format='json', ignorenonexistent=True)
            finally:
                # Always restore the original stdin
                sys.stdin = old_stdin

            call_command('backfill_avatars')

            self.message_user(request, f"Successfully cloned configuration from {peer.web_ui_onion_url}. Note: Applets were NOT cloned. Use 'Clone full BBS' to include applets.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Failed to clone configuration: {e}", messages.ERROR)
    clone_config_from_peer.short_description = "Clone configuration from peer (config only, no applets)"

    def clone_full_bbs(self, request, queryset):
        """Clone complete BBS including configuration and applets."""
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one peer to clone from.", messages.ERROR)
            return

        peer = queryset.first()

        try:
            # Run the full clone command
            from io import StringIO
            import sys

            # Capture output
            output = StringIO()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = output
            sys.stderr = output

            try:
                call_command('clone_from_bbs', peer.web_ui_onion_url)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            output_text = output.getvalue()

            if "Clone complete!" in output_text:
                self.message_user(request, f"Successfully cloned full BBS from {peer.web_ui_onion_url}. Check server logs for details.", messages.SUCCESS)
            else:
                self.message_user(request, f"Clone may have encountered issues. Output: {output_text[:200]}", messages.WARNING)
        except Exception as e:
            self.message_user(request, f"Failed to clone BBS: {e}", messages.ERROR)
            import traceback
            traceback.print_exc()
    clone_full_bbs.short_description = "Clone full BBS from peer (config + applets)"

@admin.action(description='Rekey selected file attachments')
def rekey_file_attachments(modeladmin, request, queryset):
    """Re-encrypts file attachments with new keys for federation sync"""
    import logging
    logger = logging.getLogger('core.admin')

    if not service_manager.bitsync_service:
        from core.services.bitsync_service import BitSyncService
        service_manager.bitsync_service = BitSyncService()

    if not service_manager.sync_service:
        from core.services.sync_service import SyncService
        service_manager.sync_service = SyncService()

    success_count = 0
    error_count = 0

    for attachment in queryset:
        try:
            if not attachment.metadata_manifest:
                logger.warning(f"Skipping {attachment.filename}: No manifest")
                continue

            # Decrypt existing content
            decrypted_content = service_manager.sync_service.get_decrypted_content(attachment.metadata_manifest)

            if not decrypted_content:
                logger.error(f"Failed to decrypt {attachment.filename}")
                error_count += 1
                continue

            # Parse the JSON
            file_data = json.loads(decrypted_content)

            # Create new manifest with same content
            old_hash = attachment.metadata_manifest.get('content_hash', 'N/A')[:8]
            content_hash, new_manifest = service_manager.bitsync_service.create_encrypted_content(file_data)
            new_hash = content_hash[:8]

            # Update attachment
            attachment.metadata_manifest = new_manifest
            attachment.save()

            success_count += 1
            logger.info(f"Rekeyed attachment '{attachment.filename}': {old_hash} → {new_hash}")

        except Exception as e:
            logger.error(f"Failed to rekey {attachment.filename}: {e}")
            error_count += 1

    if success_count > 0:
        modeladmin.message_user(request, f"Successfully rekeyed {success_count} attachment(s)", messages.SUCCESS)
    if error_count > 0:
        modeladmin.message_user(request, f"Failed to rekey {error_count} attachment(s)", messages.ERROR)

@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'content_type', 'size', 'author')
    search_fields = ['filename']
    actions = [federate_delete_action, rekey_file_attachments]

@admin.register(SharedLibrary)
class SharedLibraryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'library_file')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)
    autocomplete_fields = ['library_file']

# Register your models here.
admin.site.register(User, CustomUserAdmin)
admin.site.register(ValidFileType)
