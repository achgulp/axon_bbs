# Full path: axon_bbs/messaging/models.py
from django.db import models
from django.conf import settings
import uuid
from core.models import Content, FileAttachment, get_default_expires_at

class MessageBoard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    required_access_level = models.PositiveIntegerField(default=10)

    # Real-time federation fields
    is_realtime = models.BooleanField(
        default=False,
        help_text="Enable real-time federation sync for low-latency updates. "
                  "When True, messages bypass BitSync polling and use direct BBS-to-BBS push."
    )
    local_poll_interval = models.FloatField(
        default=1.0,
        help_text="Local SSE update interval in seconds. "
                  "For chat/games: 0.016 (60fps), 0.033 (30fps), 0.1 (10fps). "
                  "For boards: 1.0 (1fps). Lower = more responsive but higher CPU usage."
    )
    federation_poll_interval = models.FloatField(
        default=5.0,
        help_text="Federation sync interval in seconds. "
                  "For Tor: 5-10s (slow but private). For LAN: 0.1-1s (fast). "
                  "Federation is always slower than local updates."
    )
    use_lan_federation = models.BooleanField(
        default=False,
        help_text="Bypass Tor proxy for LAN/clearnet federation. "
                  "Enable for local network gaming (10-50ms latency). "
                  "Disable for privacy/Tor federation (1-5s latency)."
    )
    federation_room_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="Shared room identifier for federated real-time boards (e.g., 'global-chat'). "
                  "Multiple BBS instances use the same room_id to sync messages in real-time."
    )
    trusted_peers = models.JSONField(
        default=list,
        blank=True,
        help_text="List of trusted peer onion URLs for real-time sync. "
                  "Format: ['http://peer1.onion', 'http://peer2.onion'] or ['http://192.168.1.100:8000'] for LAN. "
                  "Only applies when is_realtime=True."
    )
    message_retention_days = models.PositiveIntegerField(
        default=30,
        help_text="Number of days to retain messages before automatic expiration. "
                  "Real-time boards typically use 1 day, regular boards use 30 days."
    )

    def __str__(self):
        return self.name

class Message(Content):
    board = models.ForeignKey(MessageBoard, on_delete=models.CASCADE, related_name='messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    pubkey = models.TextField(blank=True, null=True)
    metadata_manifest = models.JSONField(null=True, blank=True, help_text="BitSync manifest for P2P content distribution.")
    attachments = models.ManyToManyField(FileAttachment, blank=True, related_name='messages')
    agent_status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('processed', 'Processed'), ('failed', 'Failed')])
    last_moderated_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last moderation action on this message.")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    def __str__(self):
        return f"'{self.subject}' by {self.author.username if self.author else 'system'}"

class PrivateMessage(Content):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_mail', null=True, blank=True)
    sender_pubkey = models.TextField(blank=True, null=True)
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
