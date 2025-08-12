# Full path: axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MessageBoard, Message, PrivateMessage, TrustedInstance, Alias, BannedPubkey, ContentExtensionRequest, ValidFileType
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from .services.encryption_utils import generate_checksum

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
    list_display = ('web_ui_onion_url', 'pubkey_checksum', 'is_trusted_peer', 'added_at')
    list_display_links = ('pubkey_checksum',)
    list_filter = ('is_trusted_peer',)
    readonly_fields = ('pubkey_checksum', 'added_at')
    fieldsets = (
        (None, {
            'fields': ('web_ui_onion_url', 'pubkey', 'encrypted_private_key', 'is_trusted_peer')
        }),
        ('Timestamps', {
            'fields': ('added_at', 'last_synced_at')
        }),
    )

    # UPDATED: This line explicitly adds the 'generate_keys' function to the list of available actions.
    actions = ['generate_keys']

    @admin.display(description='Pubkey Checksum')
    def pubkey_checksum(self, obj):
        if not obj.pubkey:
            return "No pubkey"
        return generate_checksum(obj.pubkey)

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
            instance.is_trusted_peer = False  # Ensure local is not marked as trusted peer
            instance.save()
        self.message_user(request, "Keys generated and encrypted for selected instances.")
    generate_keys.short_description = "Generate and encrypt keys for selected instances"

@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'pubkey', 'verified', 'added_at')
    list_filter = ('verified',)
    search_fields = ('nickname', 'pubkey')
