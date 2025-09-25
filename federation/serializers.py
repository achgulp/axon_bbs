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
    reviewed_by = serializers.StringRelatedField()
    reported_message = MessageSerializer(read_only=True)

    class Meta:
        model = ModerationReport
        fields = ('id', 'reported_message', 'reporting_user', 'comment', 'status', 'created_at', 'reviewed_by', 'reviewed_at')

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
