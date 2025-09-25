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


# Full path: axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django import forms
from .models import User, TrustedInstance, ValidFileType, FileAttachment
from accounts.models import Alias, BannedPubkey
from messaging.models import MessageBoard, Message, PrivateMessage
from applets.models import Applet, AppletData, AppletCategory, HighScore, AppletSharedState
from federation.models import ContentExtensionRequest, ModerationReport, FederatedAction
from django.http import HttpResponseRedirect
from django.urls import path, reverse
import base64
import json
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from django.conf import settings
from django.utils.html import format_html
from django.core.management import call_command
from accounts.avatar_generator import generate_cow_avatar
from .services.encryption_utils import generate_checksum
from .services.service_manager import service_manager

def rekey_content_action(modeladmin, request, queryset):
    """Shared admin action to re-key manifests for selected content."""
    if not service_manager.bitsync_service:
        modeladmin.message_user(request, "BitSyncService is not available.", level='ERROR')
        return

    updated_count = 0
    for item in queryset:
        name = getattr(item, 'subject', getattr(item, 'filename', str(item.id)))
        try:
            if isinstance(item, Applet):
                metadata_manifest_field = 'code_manifest'
            elif isinstance(item, AppletData):
                metadata_manifest_field = 'data_manifest'
            else:
                metadata_manifest_field = 'metadata_manifest'
            metadata_manifest = getattr(item, metadata_manifest_field)

            if not metadata_manifest:
                modeladmin.message_user(request, f"Content '{name}' has no manifest to re-key.", level='WARNING')
                continue
            
            new_metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(metadata_manifest)
            
            setattr(item, metadata_manifest_field, new_metadata_manifest)
            item.save()
            updated_count += 1
        
        except Exception as e:
            modeladmin.message_user(request, f"Failed to re-key content '{name}': {e}", level='ERROR')
    
    modeladmin.message_user(request, f"Successfully updated manifests for {updated_count} item(s).")
rekey_content_action.short_description = "Re-key content for all trusted peers"

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'access_level', 'is_moderator', 'karma', 'is_staff', 'is_banned', 'is_agent', 'pubkey_checksum')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_banned', 'is_agent', 'is_moderator')
    readonly_fields = BaseUserAdmin.readonly_fields + ('pubkey_checksum', 'last_moderated_at', 'avatar_preview', 'avatar_path')
    
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        fieldsets = [
            (None, {"fields": ("username", "password")}),
            ("Personal info", {"fields": ("nickname", "first_name", "last_name", "email")}),
            ("Permissions & Roles", {"fields": ("is_active", "is_staff", "is_superuser", "is_moderator", "is_agent", "is_banned")}),
            ("BBS Stats", {"fields": ("access_level", "karma", "last_moderated_at")}),
            ("Important dates", {"fields": ("last_login", "date_joined")}),
        ]
        if obj.pubkey:
            fieldsets.insert(2, ("Avatar & Identity", {"fields": ('avatar_preview', 'avatar_path', 'pubkey')}))
        
        return tuple(fieldsets)

    @admin.display(description='Current Avatar')
    def avatar_preview(self, obj):
        if obj.avatar and obj.avatar.url:
            return format_html('<img src="{}" width="128" height="128" style="border-radius: 50%;" />', obj.avatar.url)
        return "No avatar set."
    @admin.display(description='Avatar File Path')
    def avatar_path(self, obj):
        return obj.avatar.name if obj.avatar else "N/A"

    @admin.display(description='Pubkey Checksum')
    def pubkey_checksum(self, obj):
        if not obj.pubkey:
            return "No pubkey"
        return generate_checksum(obj.pubkey)

    @admin.action(description='Update status for selected agent(s)')
    def update_agent_status(self, request, queryset):
        for user in queryset:
            is_running = user.username in service_manager.game_agents
            
            if user.is_agent and not is_running:
                if service_manager.start_agent(user):
                    self.message_user(request, f"Successfully started agent service for '{user.username}'.", level='SUCCESS')
                else:
                    self.message_user(request, f"Failed to start agent service for '{user.username}'. See logs.", level='ERROR')

            elif not user.is_agent and is_running:
                if service_manager.stop_agent(user.username):
                    self.message_user(request, f"Successfully stopped agent service for '{user.username}'.", level='SUCCESS')
                else:
                    self.message_user(request, f"Failed to stop agent service for '{user.username}'. See logs.", level='ERROR')

            elif user.is_agent and is_running:
                if service_manager.reload_agent(user.username):
                    self.message_user(request, f"Successfully reloaded agent service for '{user.username}'.", level='SUCCESS')
                else:
                    self.message_user(request, f"Failed to reload agent service for '{user.username}'. See logs.", level='ERROR')
    
    @admin.action(description="Reset selected users' avatar to default")
    def reset_avatar(self, request, queryset):
        updated_count = 0
        for user in queryset:
            if not user.pubkey:
                self.message_user(request, f"Cannot reset avatar for '{user.username}': No public key found.", level='WARNING')
                continue
            
            try:
                if user.avatar:
                    user.avatar.delete(save=False)

                avatar_content_file, avatar_filename = generate_cow_avatar(user.pubkey)
                
                user.avatar.save(avatar_filename, avatar_content_file, save=True)
                updated_count += 1
            except Exception as e:
                self.message_user(request, f"Failed to reset avatar for '{user.username}': {e}", level='ERROR')
        
        if updated_count > 0:
            self.message_user(request, f"Successfully reset avatars for {updated_count} user(s).", level='SUCCESS')

    actions = ['update_agent_status', 'reset_avatar']

@admin.register(ModerationReport)
class ModerationReportAdmin(admin.ModelAdmin):
    list_display = ('reported_message', 'reporting_user', 'status', 'created_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('status',)
    readonly_fields = ('reported_message', 'reporting_user', 'comment', 'created_at', 'reviewed_by', 'reviewed_at')

@admin.register(MessageBoard)
class MessageBoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'required_access_level')
    list_filter = ('required_access_level',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'author', 'board', 'agent_status', 'created_at', 'expires_at', 'is_pinned')
    list_filter = ('board', 'author', 'is_pinned', 'agent_status')
    date_hierarchy = 'created_at'
    actions = [rekey_content_action]

@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'recipient', 'is_read', 'created_at')
    list_filter = ('author', 'recipient', 'is_read')
    date_hierarchy = 'created_at'
    actions = [rekey_content_action]

@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'author', 'content_type', 'size', 'created_at')
    list_filter = ('author', 'content_type')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'expires_at', 'pinned_by')
    actions = [rekey_content_action]

@admin.register(BannedPubkey)
class BannedPubkeyAdmin(admin.ModelAdmin):
    list_display = ('pubkey', 'is_temporary', 'expires_at')
    list_filter = ('is_temporary',)

@admin.register(ContentExtensionRequest)
class ContentExtensionRequestAdmin(admin.ModelAdmin):
    list_display = ('content_id', 'content_type', 'user', 'request_date', 'status', 'reviewed_by')
    list_filter = ('status', 'content_type')

@admin.register(ValidFileType)
class ValidFileTypeAdmin(admin.ModelAdmin):
    list_display = ('mime_type', 'description', 'is_enabled')
    list_filter = ('is_enabled',)
    search_fields = ('mime_type', 'description')

@admin.register(TrustedInstance)
class TrustedInstanceAdmin(admin.ModelAdmin):
    list_display = ('web_ui_onion_url', 'pubkey_checksum', 'is_trusted_peer', 'last_synced_at')
    list_display_links = ('web_ui_onion_url','pubkey_checksum',)
    list_filter = ('is_trusted_peer',)
    readonly_fields = ('pubkey_checksum', 'added_at', 'last_synced_at')
    fieldsets = (
        (None, {
            'fields': ('web_ui_onion_url', 'pubkey', 'is_trusted_peer')
        }),
        ('Local Instance Details', {
            'classes': ('collapse',),
            'fields': ('encrypted_private_key',),
        }),
        ('Timestamps', {
            'fields': ('added_at', 'last_synced_at')
        }),
    )
    actions = ['generate_keys', 'fetch_peer_key', 'reset_sync_timestamp', 'run_full_uat_suite']

    @admin.action(description='Run Full UAT Suite against selected peer(s)')
    def run_full_uat_suite(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one peer to run the UAT against.", level='ERROR')
            return
        
        peer = queryset.first()
        if not peer.is_trusted_peer:
            self.message_user(request, "UAT can only be run against a trusted peer, not the local instance.", level='ERROR')
            return

        try:
            call_command('start_uat', peer.web_ui_onion_url)
            self.message_user(request, f"UAT Suite started in the background against {peer.web_ui_onion_url}. Check the UAT-Channel board for results.", level='SUCCESS')
        except Exception as e:
            self.message_user(request, f"Failed to start UAT suite: {e}", level='ERROR')

    @admin.display(description='Pubkey Checksum')
    def pubkey_checksum(self, obj):
        if not obj.pubkey:
            return "No pubkey"
        return generate_checksum(obj.pubkey)

    @admin.action(description='Generate and encrypt keys for LOCAL instance')
    def generate_keys(self, request, queryset):
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        
        for instance in queryset:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            encrypted_private = f.encrypt(private_pem.encode()).decode()
            instance.pubkey = public_key_pem
            instance.encrypted_private_key = encrypted_private
            instance.is_trusted_peer = False
            instance.save()
        self.message_user(request, "Keys generated and encrypted for selected instances.")

    @admin.action(description='Fetch public key from peer')
    def fetch_peer_key(self, request, queryset):
        updated_count = 0
        for instance in queryset:
            if not instance.web_ui_onion_url:
                self.message_user(request, f"Instance {instance.id} has no onion URL set.", level='ERROR')
                continue
            
            peer_url = instance.web_ui_onion_url.strip('/')
            target_url = f"{peer_url}/api/identity/public_key/"
            proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        
            try:
                self.message_user(request, f"Fetching key from {peer_url}...", level='INFO')
                response = requests.get(target_url, proxies=proxies, timeout=120)

                if response.status_code == 200:
                    new_key = response.json().get('public_key')
                    if new_key:
                        instance.pubkey = new_key
                        instance.save()
                        updated_count += 1
                        self.message_user(request, f"Successfully updated key for {peer_url}.", level='SUCCESS')
                    else:
                        self.message_user(request, f"Peer {peer_url} did not provide a public key.", level='ERROR')
                else:
                    self.message_user(request, f"Error fetching key from {peer_url}. Status: {response.status_code}", level='ERROR')

            except requests.exceptions.RequestException as e:
                self.message_user(request, f"Network error contacting peer {peer_url}: {e}", level='ERROR')

        if updated_count > 0:
            self.message_user(request, f"Finished. Successfully updated {updated_count} peer(s).", level='SUCCESS')
    
    @admin.action(description='Reset last synced time to force full sync')
    def reset_sync_timestamp(self, request, queryset):
        rows_updated = queryset.update(last_synced_at=None)
        self.message_user(request, f"Successfully reset sync timestamp for {rows_updated} peer(s).", level='SUCCESS')

@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'pubkey_checksum', 'verified', 'added_at')
    list_filter = ('verified',)
    search_fields = ('nickname', 'pubkey')
    readonly_fields = ('added_at', 'pubkey_checksum',)
    list_display_links = ('nickname', 'pubkey_checksum',)

    @admin.display(description='Pubkey Checksum')
    def pubkey_checksum(self, obj):
        if not obj.pubkey:
            return "No pubkey"
        return generate_checksum(obj.pubkey)

class AppletAdminForm(forms.ModelForm):
    author = forms.ModelChoiceField(
        queryset=User.objects.filter(pubkey__isnull=False),
        required=False,
        help_text="Optional: Select a local user to automatically use their public key as the author."
    )
    applet_code_file = forms.FileField(required=False, help_text="Upload a new file to generate/regenerate the manifest.")

    class Meta:
        model = Applet
        fields = '__all__'

@admin.register(AppletCategory)
class AppletCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Applet)
class AppletAdmin(admin.ModelAdmin):
    form = AppletAdminForm
    
    @admin.display(description='Code Checksum')
    def code_checksum(self, obj):
        if obj.code_manifest and 'content_hash' in obj.code_manifest:
            return obj.code_manifest['content_hash'][:16] + '...'
        return "Not Generated"

    list_display = ('name', 'category', 'event_board', 'is_local', 'created_at', 'code_checksum')
    list_filter = ('category', 'is_local')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'code_manifest', 'code_checksum')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'category', 'event_board', 'author', 'author_pubkey', ('is_local', 'is_debug_mode'), 'handles_mime_types')
        }),
        ('Code', {
            'fields': ('applet_code_file', 'code_manifest', 'code_checksum')
        }),
    )
    actions = [rekey_content_action]

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get('applet_code_file', None)
        selected_author = form.cleaned_data.get('author', None)
        
        if selected_author:
            obj.author_pubkey = selected_author.pubkey

        if not change and not uploaded_file:
            self.message_user(request, "You must upload a code file when creating a new applet.", level='ERROR')
            return

        if uploaded_file:
            js_code = uploaded_file.read().decode('utf-8')
            content_to_encrypt = {"type": "applet_code", "code": js_code}
            
            recipients = None
            if obj.is_local:
                try:
                    local_instance = TrustedInstance.objects.get(is_trusted_peer=False)
                    recipients = [local_instance.pubkey]
                except TrustedInstance.DoesNotExist:
                    self.message_user(request, "Cannot create local applet: No local instance configured.", level='ERROR')
                    return

            if not service_manager.bitsync_service:
                self.message_user(request, "BitSync service is not available. Cannot create manifest.", level='ERROR')
                return

            _content_hash, metadata_manifest = service_manager.bitsync_service.create_encrypted_content(
                content_to_encrypt, 
                recipients_pubkeys=recipients
            )
            obj.code_manifest = metadata_manifest
        
        super().save_model(request, obj, form, change)

@admin.register(AppletData)
class AppletDataAdmin(admin.ModelAdmin):
    list_display = ('applet', 'owner', 'last_updated', 'data_checksum')
    list_filter = ('applet', 'owner')
    date_hierarchy = 'last_updated'
    readonly_fields = ('id', 'last_updated', 'data_checksum')
    actions = [rekey_content_action]

    @admin.display(description='Data Checksum')
    def data_checksum(self, obj):
        if obj.data_manifest and 'content_hash' in obj.data_manifest:
            return obj.data_manifest['content_hash'][:16] + '...'
        return "N/A"

@admin.register(AppletSharedState)
class AppletSharedStateAdmin(admin.ModelAdmin):
    list_display = ('applet', 'version', 'last_updated')
    list_filter = ('applet',)
    readonly_fields = ('applet', 'version', 'state_data', 'last_updated')

    def has_add_permission(self, request):
        return False

@admin.register(HighScore)
class HighScoreAdmin(admin.ModelAdmin):
    list_display = ('applet', 'owner_nickname', 'score', 'last_updated')
    list_filter = ('applet',)
    search_fields = ('owner_nickname', 'owner_pubkey')
    readonly_fields = ('applet', 'owner_pubkey', 'owner_nickname', 'score', 'last_updated')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

admin.site.unregister(Group)
