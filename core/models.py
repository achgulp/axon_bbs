# axon_bbs/core/models.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.


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
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_agent = models.BooleanField(default=False, help_text="Designates this user as an automated agent.")
    is_moderator = models.BooleanField(default=False, help_text="Grants moderator permissions.")
    karma = models.IntegerField(default=10, help_text="User's reputation score.")
    last_moderated_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last moderation action on this user.")
    timezone = models.CharField(max_length=50, blank=True, null=True, help_text="User's preferred display timezone (IANA name).")
    
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
    
    def save(self, *args, **kwargs):
        if self.nickname:
            self.nickname = self.nickname.lower()
        if self.pubkey:
            try:
                pubkey_obj = serialization.load_pem_public_key(self.pubkey.encode())
                self.pubkey = pubkey_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode('utf-8').strip()
            except Exception as e:
                print(f"Warning: Could not normalize public key for user {self.username}: {e}")
    
        super(User, self).save(*args, **kwargs)


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
    federated_action_id = models.UUIDField(null=True, blank=True, unique=True, help_text="The ID of the federated action that created this ban.")

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
    
    def save(self, *args, **kwargs):
        if self.nickname:
            self.nickname = self.nickname.lower()
        if self.pubkey:
            try:
                pubkey_obj = serialization.load_pem_public_key(self.pubkey.encode())
                self.pubkey = pubkey_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode('utf-8').strip()
            except Exception as e:
                raise ValidationError(f"Invalid public key format for Alias: {e}")
        super(Alias, self).save(*args, **kwargs)

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
    metadata_manifest = models.JSONField(help_text="BitSync manifest for P2P file distribution.")

    def __str__(self):
        return f"{self.filename} ({self.id})"

class Message(Content):
    board = models.ForeignKey(MessageBoard, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    pubkey = models.TextField(blank=True, null=True)
    metadata_manifest = models.JSONField(null=True, blank=True, help_text="BitSync manifest for P2P content distribution.")
    attachments = models.ManyToManyField(FileAttachment, blank=True, related_name='messages')
    agent_status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('processed', 'Processed'), ('failed', 'Failed')])
    last_moderated_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last moderation action on this message.")

    def __str__(self):
        return f"'{self.subject}' by {self.author.username if self.author else 'system'}"

class PrivateMessage(Content):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_mail', null=True, blank=True)
    sender_pubkey = models.TextField(blank=True, null=True)
    recipient_pubkey = models.TextField(null=True, blank=True)
    metadata_manifest = models.JSONField(null=True, blank=True, help_text="BitSync manifest for BBS-level metadata.")
    e2e_encrypted_content = models.TextField(blank=True, null=True, help_text="The end-to-end encrypted message body and subject.")
    is_read = models.BooleanField(default=False)

    def __str__(self):
        recipient_display = "Unknown"
        if self.recipient:
            recipient_display = self.recipient.username
        else:
            recipient_display = f"ID: {str(self.id)[:8]}..."
        return f"Private Message to {recipient_display} from {self.author.username if self.author else 'system'}"

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

class FederatedAction(models.Model):
    ACTION_CHOICES = [
        ('ban_pubkey', 'Ban Pubkey'),
        ('unpin_content', 'Unpin Content'),
        ('update_profile', 'Update Profile'),
        ('DELETE_CONTENT', 'Delete Content'),
    ]
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('pending_approval', 'Pending Approval'),
        ('denied', 'Denied'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    pubkey_target = models.TextField(blank=True, null=True, help_text="The pubkey targeted by the action (e.g., for a ban).")
    content_hash_target = models.CharField(max_length=64, blank=True, null=True, help_text="The content_hash of the item being acted upon.")
    action_details = models.JSONField(default=dict, help_text="Additional details, e.g., {'is_temporary': true, 'duration_hours': 72}")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    is_logged = models.BooleanField(default=False, help_text="True if this action has been logged by the moderation agent.")

    def __str__(self):
        target = self.pubkey_target[:12] if self.pubkey_target else self.content_hash_target[:12]
        return f"'{self.action_type}' on target '{target}...'"

class ModerationReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    reported_message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, related_name='reports')
    reporting_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_filed')
    comment = models.TextField(blank=True, help_text="Reason for the report.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_logged = models.BooleanField(default=False, help_text="True if this report's outcome has been logged.")

    def __str__(self):
        return f"Report by {self.reporting_user.username} on message {self.reported_message.id if self.reported_message else '[deleted]'}"

class AppletCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Applet Categories"

    def __str__(self):
        return self.name

class Applet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="The unique name of the applet.")
    description = models.TextField(blank=True)
    author_pubkey = models.TextField(blank=True, help_text="Public key of the applet's author.")
    code_manifest = models.JSONField(help_text="BitSync manifest for the applet's code bundle.")
    is_local = models.BooleanField(default=False, help_text="If checked, this applet's code will not be swarmed to peers.")
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(AppletCategory, on_delete=models.SET_NULL, null=True, blank=True)
    is_debug_mode = models.BooleanField(default=False, help_text="Enable to show the debug console when this applet is run.")
    event_board = models.ForeignKey(MessageBoard, on_delete=models.SET_NULL, null=True, blank=True, help_text="The message board this applet will use for its public events.")

    def __str__(self):
        return self.name

class AppletData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applet = models.ForeignKey(Applet, on_delete=models.CASCADE, related_name='data_instances')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applet_data')
    data_manifest = models.JSONField(help_text="BitSync manifest for the user's applet data.")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('applet', 'owner')

    def __str__(self):
        return f"Data for '{self.applet.name}' owned by {self.owner.username}"

class AppletSharedState(models.Model):
    applet = models.OneToOneField(Applet, on_delete=models.CASCADE, primary_key=True, related_name='shared_state')
    state_data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shared State for '{self.applet.name}' (v{self.version})"


class HighScore(models.Model):
    applet = models.ForeignKey(Applet, on_delete=models.CASCADE, related_name='high_scores')
    owner_pubkey = models.TextField(db_index=True)
    owner_nickname = models.CharField(max_length=50)
    score = models.IntegerField(db_index=True)
    wins = models.IntegerField(null=True, blank=True)
    losses = models.IntegerField(null=True, blank=True)
    kills = models.IntegerField(null=True, blank=True)
    deaths = models.IntegerField(null=True, blank=True)
    assists = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField()

    class Meta:
        unique_together = ('applet', 'owner_pubkey')
        ordering = ['-score']

    def __str__(self):
        return f"{self.owner_nickname}: {self.score} on {self.applet.name}"
