# axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MessageBoard, Message, PrivateMessage, TrustedInstance, Alias, BannedPubkey, ContentExtensionRequest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

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

@admin.register(TrustedInstance)
class TrustedInstanceAdmin(admin.ModelAdmin):
    # --- CHANGE: Updated field names to match the new model ---
    list_display = ('pubkey', 'web_ui_onion_url', 'p2p_onion_address', 'added_at')
    # --- END CHANGE ---
    actions = ['generate_keys', 'generate_test_script']

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

    def generate_test_script(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one instance to generate test script.", level='error')
            return

        instance = queryset.first()
        test_magnet = "magnet:?xt=urn:btih:testkeyverification&dn=keytest"

        # Assume private key decryption for signing (in real, use load_bbs_private_key logic)
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        if instance.encrypted_private_key:
            private_pem = f.decrypt(instance.encrypted_private_key.encode()).decode()
            private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
            hash_ctx = hashes.Hash(hashes.SHA256())
            hash_ctx.update(test_magnet.encode())
            digest = hash_ctx.finalize()
            signature = private_key.sign(
                digest,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            signature_b64 = base64.b64encode(signature).decode()
        else:
            signature_b64 = "NO_PRIVATE_KEY"  # Placeholder if no key

        context = {
            'public_pem': instance.pubkey,
            'test_magnet': test_magnet,
            'signature_b64': signature_b64,
        }
        script_content = render_to_string('admin/test_key_script.txt', context)  # Use a template for the script

        response = HttpResponse(script_content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="test_keys.py"'
        return response

    generate_test_script.short_description = "Generate key test script"

@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'pubkey', 'verified', 'added_at')
    list_filter = ('verified',)
    search_fields = ('nickname', 'pubkey')
