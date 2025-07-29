# Full path: axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message, Alias, User, ContentExtensionRequest, FileAttachment
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

# --- NEW: Serializer for File Attachments ---
class FileAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for the FileAttachment model. Returns key information
    about the file after it has been processed for BitSync.
    """# Full path: axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message, Alias, User, ContentExtensionRequest, FileAttachment
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

# --- NEW: Serializer for File Attachments ---
class FileAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for the FileAttachment model. Returns key information
    about the file after it has been processed for BitSync.
    """
    class Meta:
        model = FileAttachment
        fields = ('id', 'filename', 'content_type', 'size', 'created_at')
        read_only_fields = fields

class MessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    # UPDATED: Include attachments in the message data
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'subject', 'body', 'created_at', 'author_display', 'attachments')

    def get_author_display(self, obj):
        if obj.author:
            return obj.author.nickname if obj.author.nickname else obj.author.username
        elif obj.pubkey:
            alias = Alias.objects.filter(pubkey=obj.pubkey, verified=True).first()
            if alias:
                return alias.nickname
            else:
                short_id = generate_short_id(obj.pubkey, length=8)
                return f"Moo-{short_id}"
        return 'Anonymous'

class ContentExtensionRequestSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField()
    class Meta:
        model = ContentExtensionRequest
        fields = ('id', 'content_id', 'content_type', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')
        read_only_fields = ('id', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')

    class Meta:
        model = FileAttachment
        fields = ('id', 'filename', 'content_type', 'size', 'created_at')
        read_only_fields = fields

class MessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    # UPDATED: Include attachments in the message data
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'subject', 'body', 'created_at', 'author_display', 'attachments')

    def get_author_display(self, obj):
        if obj.author:
            return obj.author.nickname if obj.author.nickname else obj.author.username
        elif obj.pubkey:
            alias = Alias.objects.filter(pubkey=obj.pubkey, verified=True).first()
            if alias:
                return alias.nickname
            else:
                short_id = generate_short_id(obj.pubkey, length=8)
                return f"Moo-{short_id}"
        return 'Anonymous'

class ContentExtensionRequestSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField()
    class Meta:
        model = ContentExtensionRequest
        fields = ('id', 'content_id', 'content_type', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')
        read_only_fields = ('id', 'user', 'request_date', 'status', 'reviewed_by', 'reviewed_at')

