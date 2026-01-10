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
    # ... (no changes to this model) ...
    access_level = models.PositiveIntegerField(default=10, help_text="User's security access level.")
    is_banned = models.BooleanField(default=False, help_text="Designates if the user is banned from the local instance.")
    pubkey = models.TextField(blank=True, null=True, help_text="User's public key (PEM).")
    nickname = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="User's chosen nickname.")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_agent = models.BooleanField(default=False, help_text="Designates this user as an automated agent.")
    agent_service_path = models.CharField(max_length=255, blank=True, null=True, help_text="Full Python path to the agent service class (e.g., applets.chat_agent_service.ChatAgentService)")
    agent_parameters = models.JSONField(default=dict, blank=True, help_text="JSON object for agent-specific parameters (e.g., poll intervals).")
    is_moderator = models.BooleanField(default=False, help_text="Grants moderator permissions.")
    karma = models.IntegerField(default=10, help_text="User's reputation score.")
    last_moderated_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last moderation action on this user.")
    timezone = models.CharField(max_length=50, blank=True, null=True, help_text="User's preferred display timezone (IANA name).")

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


class ValidFileType(models.Model):
    # ... (no changes to this model) ...
    mime_type = models.CharField(max_length=100, unique=True, help_text="e.g., 'image/jpeg'")
    description = models.CharField(max_length=255, blank=True)
    is_enabled = models.BooleanField(default=True, help_text="Disable to temporarily disallow this file type.")

    def __str__(self):
        return f"{self.mime_type} ({self.description})"


class Content(models.Model):
    # ... (no changes to this model) ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_%(class)ss', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=get_default_expires_at, null=True)
    is_pinned = models.BooleanField(default=False)
    pinned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='pinned_%(class)ss')
    class Meta:
        abstract = True


class FileAttachment(Content):
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    metadata_manifest = models.JSONField(help_text="BitSync manifest for P2P file distribution.")

    def __str__(self):
        # Format the timestamp for display in the admin dropdown.
        timestamp = self.created_at.strftime("%Y-%m-%d %H:%M")
        return f"{self.filename} ({timestamp})"


class TrustedInstance(models.Model):
    # ... (no changes to this model) ...
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

class SharedLibrary(models.Model):
    # ... (no changes to this model) ...
    """Represents a third-party library approved for use by applets."""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="A unique name for the library, e.g., 'three.js-r128' or 'jszip-v3.10.1'"
    )
    description = models.TextField(blank=True)
    library_file = models.ForeignKey(
        FileAttachment,
        on_delete=models.CASCADE,
        help_text="The FileAttachment that contains the library code."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Disable to prevent applets from loading this library."
    )

    def __str__(self):
        return self.name
