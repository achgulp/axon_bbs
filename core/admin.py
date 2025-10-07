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
    actions = ['fetch_public_key', 'force_refresh_and_rekey', 'clone_config_from_peer']

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
                from messaging.models import Message
                from core.models import FileAttachment
                all_content = list(Message.objects.all()) + list(FileAttachment.objects.all())
                for item in all_content:
                    if hasattr(item, 'metadata_manifest') and item.metadata_manifest:
                        item.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(item.metadata_manifest)
                        item.save()
                self.message_user(request, f"Forced refresh and re-keyed all content for {instance.web_ui_onion_url}.", messages.SUCCESS)
    force_refresh_and_rekey.short_description = "Force Refresh and Re-key Peer"

    def clone_config_from_peer(self, request, queryset):
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
            
            # Filter out superusers before loading data
            filtered_objects = [obj for obj in data if not (obj['model'] == 'core.user' and obj['fields']['is_superuser'])]

            out = StringIO()
            json.dump(filtered_objects, out)
            out.seek(0)

            # Use loaddata with stdin
            call_command('loaddata', '-', stdin=out, ignorenonexistent=True)
            # Backfill avatars for newly created users
            call_command('backfill_avatars')

            self.message_user(request, f"Successfully cloned configuration from {peer.web_ui_onion_url}.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Failed to clone configuration: {e}", messages.ERROR)
    clone_config_from_peer.short_description = "Clone configuration from peer"

@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'content_type', 'size', 'author')
    search_fields = ['filename']
    actions = [federate_delete_action]

@admin.register(SharedLibrary)
class SharedLibraryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'library_file')
    search_fields = ('name', 'description')
    list_filter = ('is_active',)
    autocomplete_fields = ['library_file']

# Register your models here.
admin.site.register(User, CustomUserAdmin)
admin.site.register(ValidFileType)
