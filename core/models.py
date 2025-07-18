# axon_bbs/core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import json

def get_default_expires_at():
    """Returns a default expiration time 30 days from now."""
    return timezone.now() + timedelta(days=30)

class User(AbstractUser):
    """
    Custom user model that extends Django's default AbstractUser.
    This is the central model for all registered users of the BBS.
    """
    access_level = models.PositiveIntegerField(default=10, help_text="User's security access level.")
    is_banned = models.BooleanField(default=False, help_text="Designates if the user is banned from the local instance.")

    # --- FIX FOR CLASHING REVERSE ACCESSORS ---
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

class IgnoredUser(models.Model):
    """Represents a user being ignored by another user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ignored_by')
    ignored_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ignored_users')

    class Meta:
        unique_together = ('user', 'ignored_user')

    def __str__(self):
        return f"{self.user.username} ignores {self.ignored_user.username}"

class Content(models.Model):
    """Abstract base class for user-generated content."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_%(class)ss', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_default_expires_at, null=True)
    is_pinned = models.BooleanField(default=False)
    pinned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='pinned_%(class)ss')

    class Meta:
        abstract = True

class MessageBoard(models.Model):
    """Represents a single message board or forum."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    required_access_level = models.PositiveIntegerField(default=10)
    relays = models.JSONField(default=list, blank=True, help_text="List of up to 6 Nostr relay URLs for this board (e.g., ['wss://relay.example.com']).")

    def clean(self):
        """Validate the relays field."""
        if len(self.relays) > 6:
            raise ValidationError("A message board can have at most 6 relays.")
        for relay in self.relays:
            if not isinstance(relay, str) or not relay.startswith('wss://'):
                raise ValidationError("Each relay must be a valid wss:// URL.")

    def __str__(self):
        return self.name

class Message(Content):
    """Represents a single post within a MessageBoard."""
    board = models.ForeignKey(MessageBoard, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self):
        return f"'{self.subject}' by {self.author.username if self.author else 'system'}"

class UploadedFile(Content):
    """Represents a single file uploaded by a user."""
    file = models.FileField(upload_to='uploads/')
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.file.name

class PrivateMessage(Content):
    """Represents a private mail message between two users."""
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_mail')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.author if self.author else 'system'} to {self.recipient}: '{self.subject}'"

class ContentExtensionRequest(models.Model):
    """Represents a user's request to extend the lifespan of their content."""
    content_id = models.UUIDField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Extension request for content {self.content_id} by {self.user.username}"
