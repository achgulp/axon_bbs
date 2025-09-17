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
# Full path: axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message, User, ContentExtensionRequest, FileAttachment, PrivateMessage, Applet, HighScore, ModerationReport, FederatedAction
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_salt, generate_short_id
from core.services.avatar_generator import generate_cow_avatar
import os
import logging
import json

logger = logging.getLogger(__name__)
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    nickname = serializers.CharField(required=True)
    security_question_1 = serializers.CharField(write_only=True, required=True)
    security_answer_1 = serializers.CharField(write_only=True, required=True)
    security_question_2 = serializers.CharField(write_only=True, required=True)
    security_answer_2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'nickname', 'security_question_1', 'security_answer_1', 'security_question_2', 'security_answer_2')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            nickname=validated_data.get('nickname')
        )
        try:
            identity_service = IdentityService(user=user)
            identity = identity_service.generate_identity_with_manifest(
                password=validated_data['password'],
                sq1=validated_data['security_question_1'],
                sa1=validated_data['security_answer_1'],
                sq2=validated_data['security_question_2'],
                sa2=validated_data['security_answer_2']
            )
            user.pubkey = identity['public_key']
            
            avatar_content_file, avatar_filename = generate_cow_avatar(user.pubkey)
            user.avatar.save(avatar_filename, avatar_content_file, save=False)

            user.save()
            logger.info(f"Successfully created manifest-based identity for {user.username}")
        except Exception as e:
            logger.error(f"Failed to create identity for {user.username}. Rolling back user creation. Error: {e}")
            user.delete()
            raise serializers.ValidationError({"identity_error": "Failed to create identity during registration."})
        return user

class MessageBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBoard
        fields = ('id', 'name', 'description')

class FileAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAttachment
        fields = ('id', 'filename', 'content_type', 'size', 'created_at')
        read_only_fields = fields

class MessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    author_avatar_url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'subject', 'body', 'created_at', 'author_display', 'author_avatar_url', 'attachments', 'pubkey')

    def get_author_display(self, obj):
        user_to_check = obj.author
        if not user_to_check and obj.pubkey:
            user_to_check = User.objects.filter(pubkey=obj.pubkey).first()

        if user_to_check:
            return user_to_check.nickname if user_to_check.nickname else user_to_check.username
        elif obj.pubkey:
             short_id = generate_short_id(obj.pubkey, length=8)
             return f"Moo-{short_id}"
        
        return 'Anonymous'
    
    def get_author_avatar_url(self, obj):
        user_to_check = obj.author
        if not user_to_check and obj.pubkey:
            user_to_check = User.objects.filter(pubkey=obj.pubkey).first()

        if user_to_check and user_to_check.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user_to_check.avatar.url)
            return user_to_check.avatar.url
        return None

class PrivateMessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    author_avatar_url = serializers.SerializerMethodField()
    decrypted_body = serializers.CharField(read_only=True)
    
    class Meta:
        model = PrivateMessage
        fields = ('id', 'subject', 'decrypted_body', 'created_at', 'is_read', 'author_display', 'author_avatar_url')
        read_only_fields = fields

    def get_author_display(self, obj):
        if obj.author:
            return obj.author.nickname if obj.author.nickname else obj.author.username
        elif obj.sender_pubkey:
            user = User.objects.filter(pubkey=obj.sender_pubkey).first()
            if user:
                return user.nickname if user.nickname else user.username
            short_id = generate_short_id(obj.sender_pubkey, length=8)
            return f"Moo-{short_id}"
        return "Unknown Sender"
    
    def get_author_avatar_url(self, obj):
        user_to_check = obj.author
        if not user_to_check and obj.sender_pubkey:
             user_to_check = User.objects.filter(pubkey=obj.sender_pubkey).first()

        if user_to_check and user_to_check.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user_to_check.avatar.url)
            return user_to_check.avatar.url
        return None

class PrivateMessageOutboxSerializer(serializers.ModelSerializer):
    recipient_display = serializers.SerializerMethodField()
    recipient_avatar_url = serializers.SerializerMethodField()
    decrypted_body = serializers.CharField(read_only=True)
    
    class Meta:
        model = PrivateMessage
        fields = ('id', 'subject', 'decrypted_body', 'created_at', 'is_read', 'recipient_display', 'recipient_avatar_url', 'recipient_pubkey')
        read_only_fields = fields

    def get_recipient_display(self, obj):
        user_to_check = obj.recipient
        if not user_to_check and obj.recipient_pubkey:
            user_to_check = User.objects.filter(pubkey=obj.recipient_pubkey).first()

        if user_to_check:
            return user_to_check.nickname if user_to_check.nickname else user_to_check.username
        elif obj.recipient_pubkey:
            short_id = generate_short_id(obj.recipient_pubkey, length=8)
            return f"Moo-{short_id}"
        return 'Unknown Recipient'

    def get_recipient_avatar_url(self, obj):
        user_to_check = obj.recipient
        if not user_to_check and obj.recipient_pubkey:
            user_to_check = User.objects.filter(pubkey=obj.recipient_pubkey).first()
        
        if user_to_check and user_to_check.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user_to_check.avatar.url)
            return user_to_check.avatar.url
        return None

class ContentExtensionRequestSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField()
    class Meta:
        model = ContentExtensionRequest
        fields = ('id', 'content_id', 'content_type', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')
        read_only_fields = ('id', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')

class AppletSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    class Meta:
        model = Applet
        fields = ('id', 'name', 'description', 'author_pubkey', 'code_manifest', 'created_at', 'category_name', 'is_debug_mode')
        read_only_fields = fields

class HighScoreSerializer(serializers.ModelSerializer):
    owner_avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = HighScore
        fields = ('owner_nickname', 'owner_avatar_url', 'score', 'wins', 'losses', 'kills', 'deaths', 'assists', 'last_updated')

    def get_owner_avatar_url(self, obj):
        user = User.objects.filter(pubkey=obj.owner_pubkey).first()
        if user and user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user.avatar.url)
            return user.avatar.url
        return None

class ModerationReportSerializer(serializers.ModelSerializer):
    reporting_user = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField()
    reported_message = MessageSerializer(read_only=True)

    class Meta:
        model = ModerationReport
        fields = ('id', 'reported_message', 'reporting_user', 'comment', 'status', 'created_at', 'reviewed_by', 'reviewed_at')

class FederatedActionProfileUpdateSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    # --- NEW FIELD ---
    pending_avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = FederatedAction
        fields = ('id', 'created_at', 'action_details', 'user_info', 'pending_avatar_url')

    def get_user_info(self, obj):
        user = User.objects.filter(pubkey=obj.pubkey_target).first()
        if not user:
            return None
        
        request = self.context.get('request')
        avatar_url = None
        if user.avatar:
            avatar_url = request.build_absolute_uri(user.avatar.url) if request else user.avatar.url
        
        return {
            "username": user.username,
            "current_nickname": user.nickname,
            "current_avatar_url": avatar_url
        }
    
    # --- NEW METHOD ---
    def get_pending_avatar_url(self, obj):
        avatar_hash = obj.action_details.get('avatar_hash')
        if not avatar_hash:
            return None
        
        request = self.context.get('request')
        if request:
            # Construct a URL to the new preview endpoint
            return request.build_absolute_uri(f'/api/moderation/preview_content/{avatar_hash}/')
        return None
