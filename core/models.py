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
    pubkey = models.TextField(blank=True, null=True, help_text="User's public key (PEM).")
    nickname = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="User's chosen nickname.")

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

class IgnoredPubkey(models.Model):
    """Represents a public key being ignored by a user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ignored_pubkeys')
    pubkey = models.TextField()

    class Meta:
        unique_together = ('user', 'pubkey')

    def __str__(self):
        return f"{self.user.username} ignores pubkey starting with {self.pubkey[:12]}..."

class BannedPubkey(models.Model):
    """Represents a banned public key on the platform."""
    pubkey = models.TextField(unique=True)
    is_temporary = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="If the ban is temporary, this is when it expires.")

    def __str__(self):
        status = "Temporarily Banned" if self.is_temporary and self.expires_at and self.expires_at > timezone.now() else "Banned"
        return f"[{status}] pubkey starting with {self.pubkey[:12]}..."

    def save(self, *args, **kwargs):
        if self.is_temporary and not self.expires_at:
            # Set a default temporary ban duration if not specified, e.g., 72 hours.
            self.expires_at = timezone.now() + timedelta(hours=72)
        if not self.is_temporary:
            self.expires_at = None
        super().save(*args, **kwargs)

class Alias(models.Model):
    pubkey = models.TextField(unique=True)
    nickname = models.CharField(max_length=50)
    verified = models.BooleanField(default=False)  # True if signature checked
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "aliases"

    def __str__(self):
        return f"{self.nickname} ({self.pubkey[:12]}...)"

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

    def __str__(self):
        return self.name

class Message(Content):
    """Represents a single post within a MessageBoard."""
    board = models.ForeignKey(MessageBoard, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()  # JSON for threads
    pubkey = models.TextField(blank=True, null=True)

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
    body = models.TextField()  # Encrypted JSON
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.author if self.author else 'system'} to {self.recipient}: '{self.subject}'"

class ContentExtensionRequest(models.Model):
    """Represents a user's request to extend the lifespan of their content."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    
    content_id = models.UUIDField()
    content_type = models.CharField(max_length=20) # e.g., 'message', 'uploadedfile'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Extension request for content {self.content_id} by {self.user.username} ({self.status})"

class TrustedInstance(models.Model):
    pubkey = models.TextField(blank=True, unique=True)
    onion_url = models.URLField(blank=True, help_text="Full .onion URL for the peer (e.g., http://example.onion:6881)")
    encrypted_private_key = models.TextField(blank=True)  # Encrypted with SECRET_KEY-derived Fernet
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pubkey
