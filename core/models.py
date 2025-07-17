# axon_bbs/core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    """
    Custom user model that extends Django's default AbstractUser.
    This is the central model for all registered users of the BBS.
    """
    access_level = models.PositiveIntegerField(default=10, help_text="User's security access level.")

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

class MessageBoard(models.Model):
    """Represents a single message board or forum."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    required_access_level = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name

class Message(models.Model):
    """Represents a single post within a MessageBoard."""
    board = models.ForeignKey(MessageBoard, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    posted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"'{self.subject}' by {self.author.username}"

class FileArea(models.Model):
    """Represents a directory or area for file uploads."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    view_access_level = models.PositiveIntegerField(default=10)
    upload_access_level = models.PositiveIntegerField(default=20)

    def __str__(self):
        return self.name

class UploadedFile(models.Model):
    """Represents a single file uploaded by a user."""
    area = models.ForeignKey(FileArea, on_delete=models.CASCADE, related_name='files')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    description = models.CharField(max_length=255, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class PrivateMessage(models.Model):
    """Represents a private mail message between two users."""
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_mail')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_mail')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} to {self.recipient}: '{self.subject}'"

