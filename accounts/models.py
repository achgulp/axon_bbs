# Full path: axon_bbs/accounts/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cryptography.hazmat.primitives import serialization
from django.utils import timezone
from datetime import timedelta

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