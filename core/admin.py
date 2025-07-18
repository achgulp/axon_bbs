# axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MessageBoard, Message, PrivateMessage, TrustedInstance, Alias
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import base64
from django.conf import settings

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'access_level', 'is_staff', 'is_banned')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('BBS Info', {'fields': ('access_level', 'is_banned')}),
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

@admin.register(TrustedInstance)
class TrustedInstanceAdmin(admin.ModelAdmin):
    list_display = ('pubkey', 'onion_url', 'added_at')
    actions = ['generate_keys']

    def generate_keys(self, request, queryset):
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])  # Derive Fernet key
        f = Fernet(key)

        for instance in queryset:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')

            encrypted_private = f.encrypt(private_pem.encode()).decode()

            instance.pubkey = public_key
            instance.encrypted_private_key = encrypted_private
            instance.save()

        self.message_user(request, "Keys generated and encrypted for selected instances.")

    generate_keys.short_description = "Generate and encrypt keys"

@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'pubkey', 'verified', 'added_at')
    list_filter = ('verified',)
    search_fields = ('nickname', 'pubkey')
