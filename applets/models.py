# Axon BBS - a modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/applets/models.py
from django.db import models
from django.conf import settings
import uuid
from messaging.models import MessageBoard

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
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="The user who owns and can manage this applet.")
    
    author_pubkey = models.TextField(blank=True, help_text="Public key of the applet's author. Automatically set if an owner is selected.")
    code_manifest = models.JSONField(help_text="BitSync manifest for the applet's code bundle.")
    parameters = models.JSONField(default=dict, blank=True, help_text="JSON object for applet-specific parameters (e.g., asset hashes or required libraries).")
    is_local = models.BooleanField(default=False, help_text="If checked, this applet's code will not be swarmed to peers.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(AppletCategory, on_delete=models.SET_NULL, null=True, blank=True)
    is_debug_mode = models.BooleanField(default=False, help_text="Enable to show the debug console when this applet is run.")
    event_board = models.ForeignKey(MessageBoard, on_delete=models.SET_NULL, null=True, blank=True, help_text="The message board this applet will use for its public events.")
    handles_mime_types = models.CharField(max_length=255, blank=True, help_text="Comma-separated list of MIME types this applet can view (e.g., image/png,image/jpeg)")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Automatically set the author_pubkey if an owner is assigned and has a pubkey
        if self.owner and self.owner.pubkey:
            self.author_pubkey = self.owner.pubkey
        super().save(*args, **kwargs)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applet_id = models.CharField(max_length=100, db_index=True, default='', help_text="The applet instance ID (for backward compatibility)")
    room_id = models.CharField(max_length=100, unique=True, db_index=True, default='', help_text="The shared room ID (allows multiple applet instances to share state)")
    state_data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shared State for room '{self.room_id}' (v{self.version})"


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
