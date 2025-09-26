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


# Full path: axon_bbs/federation/serializers.py
from rest_framework import serializers
from django.conf import settings
import os
from .models import ContentExtensionRequest, ModerationReport, FederatedAction
from messaging.serializers import MessageSerializer
from core.models import User


class ContentExtensionRequestSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField()
    
    class Meta:
        model = ContentExtensionRequest
        fields = ('id', 'content_id', 'content_type', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')
        read_only_fields = ('id', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')

class ModerationReportSerializer(serializers.ModelSerializer):
    reporting_user = serializers.StringRelatedField()
    # NEW: Added a field to get the reporting user's public key
    reporting_user_pubkey = serializers.CharField(source='reporting_user.pubkey', read_only=True)
    reviewed_by = serializers.StringRelatedField()
    reported_message = MessageSerializer(read_only=True)

    class Meta:
        model = ModerationReport
        # MODIFIED: Added reporting_user_pubkey to the list of fields
        fields = ('id', 'reported_message', 'reporting_user', 'reporting_user_pubkey', 'comment', 'status', 'created_at', 'reviewed_by', 'reviewed_at', 'report_type')

class ModerationInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationReport
        fields = ('comment',)

class FederatedActionProfileUpdateSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    pending_avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FederatedAction
        fields = ('id', 'created_at', 'action_details', 'user_info', 'pending_avatar_url')

    def get_user_info(self, obj):
        user = User.objects.filter(pubkey=obj.pubkey_target).first()
        if not user:
            return {
                "username": "Unknown/Federated User",
                "current_nickname": "N/A",
                "current_avatar_url": None
            }
        
        request = self.context.get('request')
        avatar_url = None
        if user.avatar:
            avatar_url = request.build_absolute_uri(user.avatar.url) if request else user.avatar.url
        
        return {
            "username": user.username,
            "current_nickname": user.nickname,
            "current_avatar_url": avatar_url
        }
    
    def get_pending_avatar_url(self, obj):
        temp_filename = obj.action_details.get('pending_avatar_filename')
        
        if not temp_filename:
            return None
        
        request = self.context.get('request')
        if request:
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            return request.build_absolute_uri(os.path.join(media_url, 'pending_avatars', temp_filename))
        return None
