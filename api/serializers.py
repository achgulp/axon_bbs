# Full path: axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message, Alias, User, ContentExtensionRequest
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_salt, generate_short_id
import os
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model. Handles creation of the user's identity on registration.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password')

    def create(self, validated_data):
        # Implementation remains the same
        pass

class MessageBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBoard
        fields = ('id', 'name', 'description')

class MessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'subject', 'body', 'created_at', 'author_display')
        read_only_fields = ('id', 'created_at')

    def get_author_display(self, obj):
        """
        Determines the correct display name for a message's author.
        - For local users, it uses their nickname or username.
        - For synced remote users, it looks up their verified Alias via their pubkey.
        """
        # Case 1: The author is a local user on this BBS instance.
        if obj.author:
            return obj.author.nickname if obj.author.nickname else obj.author.username
        
        # Case 2: The message is from a remote peer and only has a pubkey.
        elif obj.pubkey:
            # Look for a verified nickname associated with this public key.
            alias = Alias.objects.filter(pubkey=obj.pubkey, verified=True).first()
            if alias:
                return alias.nickname
            else:
                # Fallback for a remote user without a known alias.
                short_id = generate_short_id(obj.pubkey, length=8)
                return f"Peer-{short_id}"
        
        # Fallback case if no author or pubkey is present.
        return 'Anonymous'

class ContentExtensionRequestSerializer(serializers.ModelSerializer):
    # Implementation remains the same
    pass

