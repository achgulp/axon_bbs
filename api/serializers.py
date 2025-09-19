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


# Full path: axon_bbs/api/serializers.py

from rest_framework import serializers
from core.models import Message, PrivateMessage, MessageBoard, User
from core.services.encryption_utils import decrypt_for_recipients_only, generate_checksum
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'pubkey', 'karma']

class MessageBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBoard
        fields = ['id', 'name', 'description', 'required_sl']

class MessageSerializer(serializers.ModelSerializer):
    author_display = serializers.CharField(source='author.nickname', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'subject', 'body', 'author_display', 'created_at', 'board']

class PrivateMessageOutboxSerializer(serializers.ModelSerializer):
    """
    Serializer for sender's outbox: Dynamically decrypts subject/body for sender view.
    Uses SerializerMethodField to avoid model field validation errors.
    """
    subject = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    recipient_display = serializers.CharField(source='recipient.nickname', read_only=True)
    
    class Meta:
        model = PrivateMessage
        fields = ['id', 'subject', 'body', 'recipient_display', 'created_at', 'sent_at']
    
    def get_subject(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return "[Decryption Failed: Not Logged In]"
        try:
            # Assume user's private key is accessible via session or service (in real impl, fetch from identity_service)
            user_private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC... (mock; replace with actual fetch)\n-----END PRIVATE KEY-----"
            user_checksum = generate_checksum(request.user.pubkey)
            return decrypt_for_recipients_only(
                obj.e2e_manifest, user_checksum, user_private_key, obj.encrypted_subject
            )
        except Exception as e:
            logger.error(f"Subject decryption failed for PM {obj.id}: {e}")
            return "[Decryption Error]"
    
    def get_body(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return "[Decryption Failed: Not Logged In]"
        try:
            user_private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC... (mock; replace with actual fetch)\n-----END PRIVATE KEY-----"
            user_checksum = generate_checksum(request.user.pubkey)
            return decrypt_for_recipients_only(
                obj.e2e_manifest, user_checksum, user_private_key, obj.encrypted_body
            )
        except Exception as e:
            logger.error(f"Body decryption failed for PM {obj.id}: {e}")
            return "[Decryption Error]"

class PrivateMessageInboxSerializer(serializers.ModelSerializer):
    # Similar to Outbox, but for recipient view
    subject = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    sender_display = serializers.CharField(source='sender.nickname', read_only=True)
    
    class Meta:
        model = PrivateMessage
        fields = ['id', 'subject', 'body', 'sender_display', 'created_at', 'read_at']
    
    # Reuse get_subject/get_body logic from Outbox, as decryption is symmetric for sender/recipient

# Additional serializers (e.g., for boards, etc.) can go here...
