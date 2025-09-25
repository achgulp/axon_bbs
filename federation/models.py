# Full path: axon_bbs/federation/models.py
from django.db import models
from django.conf import settings
import uuid
from messaging.models import Message

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