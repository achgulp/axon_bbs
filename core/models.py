# Full path: axon_bbs/core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import json
from cryptography.hazmat.primitives import serialization

def get_default_expires_at():
    """Returns a default expiration time from now based on settings."""
    days = getattr(settings, 'DEFAULT_CONTENT_LIFESPAN_DAYS', 30)
    return timezone.now() + timedelta(days=days)

class User(AbstractUser):
    access_level = models.PositiveIntegerField(default=10, help_text="User's security access level.")
    is_banned = models.BooleanField(default=False, help_text="Designates if the user is banned from the local instance.")
    pubkey = models.TextField(blank=True, null=True, help_text="User's public key (PEM).")
    nickname = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="User's chosen nickname.")
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="core_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="core_user_set",
        related_query_name="user",
    )
    def __str__(self):
        return self.username

class IgnoredPubkey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ignored_pubkeys')
    pubkey = models.TextField()
    class Meta:
        unique_together = ('user', 'pubkey')
    def __str__(self):
        return f"{self.user.username} ignores pubkey starting with {self.pubkey[:12]}..."

class BannedPubkey(models.Model):
    pubkey = models.TextField(unique=True)
    is_temporary = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="If the ban is temporary, this is when it expires.")
    def __str__(self):
        status = "Temporarily Banned" if self.is_temporary and self.expires_at and self.expires_at > timezone.now() else "Banned"
        return f"[{status}] pubkey starting with {self.pubkey[:12]}..."
    def save(self, *args, **kwargs):
        if self.is_temporary and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=72)
        if not self.is_temporary:
            self.expires_at = None
        super().save(*args, **kwargs)

class Alias(models.Model):
    pubkey = models.TextField(unique=True)
    nickname = models.CharField(max_length=50, unique=True)
    verified = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name_plural = "aliases"
    def __str__(self):
        return f"{self.nickname} ({self.pubkey[:12]}...)"

class ValidFileType(models.Model):
    mime_type = models.CharField(max_length=100, unique=True, help_text="e.g., 'image/jpeg'")
    description = models.CharField(max_length=255, blank=True)
    is_enabled = models.BooleanField(default=True, help_text="Disable to temporarily disallow this file type.")

    def __str__(self):
        return f"{self.mime_type} ({self.description})"

class Content(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_%(class)ss', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_default_expires_at, null=True)
    is_pinned = models.BooleanField(default=False)
    pinned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='pinned_%(class)ss')
    class Meta:
        abstract = True

class MessageBoard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    required_access_level = models.PositiveIntegerField(default=10)
    def __str__(self):
        return self.name

class FileAttachment(Content):
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    manifest = models.JSONField(help_text="BitSync manifest for P2P file distribution.")

    def __str__(self):
        return f"{self.filename} ({self.id})"

class Message(Content):
    board = models.ForeignKey(MessageBoard, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    pubkey = models.TextField(blank=True, null=True)
    manifest = models.JSONField(null=True, blank=True, help_text="BitSync manifest for P2P content distribution.")
    attachments = models.ManyToManyField(FileAttachment, blank=True, related_name='messages')

    def __str__(self):
        return f"'{self.subject}' by {self.author.username if self.author else 'system'}"

class PrivateMessage(Content):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_mail', null=True, blank=True)
    recipient_pubkey = models.TextField()
    subject = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    manifest = models.JSONField(null=True, blank=True, help_text="BitSync manifest for E2E encrypted content.")

    def __str__(self):
        recipient_display = "Unknown"
        if self.recipient:
            recipient_display = self.recipient.username
        else:
            recipient_display = f"PubKey starting with {self.recipient_pubkey[:12]}..."
        return f"'{self.subject}' to {recipient_display} from {self.author.username if self.author else 'system'}"

class TrustedInstance(models.Model):
    web_ui_onion_url = models.URLField(max_length=255, blank=True, null=True)
    pubkey = models.TextField(blank=True, null=True)
    encrypted_private_key = models.TextField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(blank=True, null=True)
    is_trusted_peer = models.BooleanField(default=False, help_text="Check if this is a trusted peer (uncheck for local).")
    def save(self, *args, **kwargs):
        if self.pubkey:
            try:
                pubkey_obj = serialization.load_pem_public_key(self.pubkey.encode())
                self.pubkey = pubkey_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode('utf-8').strip()
            except Exception as e:
                raise ValidationError(f"Invalid public key format: {e}")
        super().save(*args, **kwargs)
    def __str__(self):
        return self.web_ui_onion_url or "Local Instance"

class ContentExtensionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    content_id = models.UUIDField()
    content_type = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_extensions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        unique_together = ('content_id', 'user')
    def __str__(self):
        return f"Extension Request for {self.content_type} {self.id} by {self.user.username}"
