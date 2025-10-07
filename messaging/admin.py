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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/messaging/admin.py
from django.contrib import admin
from .models import MessageBoard, Message, PrivateMessage
from federation.models import FederatedAction

@admin.action(description='Federate Delete (broadcasts delete to peers)')
def federate_delete_action(modeladmin, request, queryset):
    for item in queryset:
        if hasattr(item, 'metadata_manifest') and item.metadata_manifest:
            content_hash = item.metadata_manifest.get('content_hash')
            if content_hash:
                FederatedAction.objects.create(
                    action_type='DELETE_CONTENT',
                    content_hash_target=content_hash,
                    action_details={'reason': f'Content deleted by admin {request.user.username}'}
                )
    queryset.delete()

class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'author', 'board', 'created_at')
    list_filter = ('board', 'author')
    actions = [federate_delete_action]

# Register your models here.
admin.site.register(MessageBoard)
admin.site.register(Message, MessageAdmin)
admin.site.register(PrivateMessage)
