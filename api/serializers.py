# Full path: axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message, Alias, User, ContentExtensionRequest, FileAttachment, PrivateMessage, Applet, HighScore
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_salt, generate_short_id
import os
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ('username', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )
        try:
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            os.makedirs(user_data_dir, exist_ok=True)
            salt = generate_salt()
            with open(os.path.join(user_data_dir, 'salt.bin'), 'wb') as f:
                f.write(salt)
            encryption_key = derive_key_from_password(validated_data['password'], salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(
                storage_path=identity_storage_path,
                encryption_key=encryption_key
            )
            identity = identity_service.generate_and_add_identity(name="default")
            user.pubkey = identity['public_key']
            user.save()
            logger.info(f"Successfully created initial identity for {user.username}")
        except Exception as e:
            logger.error(f"Failed to create identity for {user.username}. Rolling back user creation. Error: {e}")
            user.delete()
            raise e
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
        if obj.author:
            return obj.author.nickname if obj.author.nickname else obj.author.username
        elif obj.pubkey:
            alias = Alias.objects.filter(pubkey=obj.pubkey).first()
            if alias:
                return alias.nickname
            else:
                short_id = generate_short_id(obj.pubkey, length=8)
                return f"Moo-{short_id}"
        
        return 'Anonymous'
    
    def get_author_avatar_url(self, obj):
        if obj.author and obj.author.avatar:
            return obj.author.avatar.url
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
            alias = Alias.objects.filter(pubkey=obj.sender_pubkey).first()
            if alias:
                return alias.nickname
            else:
                short_id = generate_short_id(obj.sender_pubkey, length=8)
                return f"Moo-{short_id}"
        return "Unknown Sender"
    
    def get_author_avatar_url(self, obj):
        # In the inbox, the author is the sender
        if obj.author and obj.author.avatar:
            return obj.author.avatar.url
        # For remote users, find the local user record via pubkey
        if obj.sender_pubkey:
            user = User.objects.filter(pubkey=obj.sender_pubkey).first()
            if user and user.avatar:
                return user.avatar.url
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
        if obj.recipient:
            return obj.recipient.nickname if obj.recipient.nickname else obj.recipient.username
        elif obj.recipient_pubkey:
            alias = Alias.objects.filter(pubkey=obj.recipient_pubkey).first()
            if alias:
                return alias.nickname
            else:
                short_id = generate_short_id(obj.recipient_pubkey, length=8)
                return f"Moo-{short_id}"
        return 'Unknown Recipient'

    def get_recipient_avatar_url(self, obj):
        if obj.recipient and obj.recipient.avatar:
            return obj.recipient.avatar.url
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
        fields = ('id', 'name', 'description', 'author_pubkey', 'code_manifest', 'created_at', 'category_name')
        read_only_fields = fields

class HighScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighScore
        # UPDATED: Add all new stat fields to the serializer
        fields = ('owner_nickname', 'score', 'wins', 'losses', 'kills', 'deaths', 'assists', 'last_updated')
