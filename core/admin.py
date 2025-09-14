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


# Full path: axon_bbs/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django import forms
from .models import User, MessageBoard, Message, PrivateMessage, TrustedInstance, Alias, BannedPubkey, ContentExtensionRequest, ValidFileType, FileAttachment, Applet, AppletData, AppletCategory, HighScore, AppletSharedState, ModerationReport
from django.http import HttpResponseRedirect
from django.urls import path, reverse
import base64
import json
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from django.conf import settings
from .services.encryption_utils import generate_checksum
from .services.service_manager import service_manager

def rekey_content_action(modeladmin, request, queryset):
    """Shared admin action to re-key manifests for selected content."""
    # ... (this function remains unchanged) ...

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'access_level', 'is_moderator', 'karma', 'is_staff', 'is_banned', 'is_agent', 'pubkey_checksum')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_banned', 'is_agent', 'is_moderator')
    readonly_fields = BaseUserAdmin.readonly_fields + ('pubkey_checksum', 'last_moderated_at',)
    
    # --- MODIFIED: Use get_fieldsets for robust display logic ---
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if request.user.is_superuser:
            return (
                (None, {"fields": ("username", "password")}),
                ("Personal info", {"fields": ("nickname", "first_name", "last_name", "email", "pubkey")}),
                ("Permissions & Roles", {"fields": ("is_active", "is_staff", "is_superuser", "is_moderator", "is_agent", "is_banned")}),
                ("BBS Stats", {"fields": ("access_level", "karma", "last_moderated_at")}),
                ("Important dates", {"fields": ("last_login", "date_joined")}),
            )
        else:
            fieldsets = list(super().get_fieldsets(request, obj))
            fieldsets.append(
                ("BBS Info", {
                    "fields": ("nickname", "pubkey", "access_level", "karma", "is_moderator", "is_agent", "is_banned", "last_moderated_at")
                })
            )
            return fieldsets

    @admin.display(description='Pubkey Checksum')
    def pubkey_checksum(self, obj):
        if not obj.pubkey:
            return "No pubkey"
        return generate_checksum(obj.pubkey)

    # --- MODIFIED: Admin action is now smarter ---
    @admin.action(description='Update status for selected agent(s)')
    def update_agent_status(self, request, queryset):
        for user in queryset:
            is_running = user.username in service_manager.game_agents
            
            if user.is_agent and not is_running:
                # Agent flag is ON, but service is NOT running -> START IT
                if service_manager.start_agent(user):
                    self.message_user(request, f"Successfully started agent service for '{user.username}'.", level='SUCCESS')
                else:
                    self.message_user(request, f"Failed to start agent service for '{user.username}'. See logs.", level='ERROR')

            elif not user.is_agent and is_running:
                # Agent flag is OFF, but service IS running -> STOP IT
                if service_manager.stop_agent(user.username):
                    self.message_user(request, f"Successfully stopped agent service for '{user.username}'.", level='SUCCESS')
                else:
                    self.message_user(request, f"Failed to stop agent service for '{user.username}'. See logs.", level='ERROR')

            elif user.is_agent and is_running:
                # Agent flag is ON, and service IS running -> RELOAD IT
                if service_manager.reload_agent(user.username):
                    self.message_user(request, f"Successfully reloaded agent service for '{user.username}'.", level='SUCCESS')
                else:
                    self.message_user(request, f"Failed to reload agent service for '{user.username}'. See logs.", level='ERROR')

    actions = ['update_agent_status']
    # --- END MODIFICATION ---

# ... (The rest of the file remains unchanged) ...

@admin.register(ModerationReport)
class ModerationReportAdmin(admin.ModelAdmin):
    list_display = ('reported_message', 'reporting_user', 'status', 'created_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('status',)
    readonly_fields = ('reported_message', 'reporting_user', 'comment', 'created_at', 'reviewed_by', 'reviewed_at')
    
# ... (rest of the file is the same as the last version I provided) ...
admin.site.unregister(Group)
