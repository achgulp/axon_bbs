# Full path: axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MessageBoard, Message, PrivateMessage, TrustedInstance, Alias, BannedPubkey, ContentExtensionRequest, ValidFileType
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import json
import requests
from django.conf import settings
from .services.encryption_utils import generate_checksum
from .services.service_manager import service_manager

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'access_level', 'is_staff', 'is_banned')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('BBS Info', {'fields': ('access_level', 'is_banned', 'pubkey', 'nickname')}),
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'is_banned')

@admin.register(MessageBoard)
class MessageBoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'required_access_level')
    list_filter = ('required_access_level',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'author', 'board', 'created_at', 'expires_at', 'is_pinned')
    list_filter = ('board', 'author', 'is_pinned')
    date_hierarchy = 'created_at'
    actions = ['rekey_messages']

    @admin.action(description='Re-key message for all trusted peers')
    def rekey_messages(self, request, queryset):
        if not service_manager.bitsync_service:
            self.message_user(request, "BitSyncService is not available.", level='ERROR')
            return

        updated_count = 0
        for message in queryset:
            try:
                if not message.manifest:
                    self.message_user(request, f"Message '{message.subject}' has no manifest to re-key.", level='WARNING')
                    continue
                
                new_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(message.manifest)
                
                message.manifest = new_manifest
                message.save()
                updated_count += 1
            except Exception as e:
                self.message_user(request, f"Failed to re-key message '{message.subject}': {e}", level='ERROR')
        
        self.message_user(request, f"Successfully updated manifests for {updated_count} message(s).")

@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'author', 'recipient', 'created_at', 'is_read')
    list_filter = ('author', 'recipient', 'is_read')
    date_hierarchy = 'created_at'

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
    actions = ['generate_keys', 'fetch_peer_key', 'reset_sync_timestamp']

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
    list_display = ('nickname', 'pubkey', 'verified', 'added_at')
    list_filter = ('verified',)
    search_fields = ('nickname', 'pubkey')
