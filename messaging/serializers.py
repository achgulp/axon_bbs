# Full path: axon_bbs/messaging/serializers.py
from rest_framework import serializers
from .models import MessageBoard, Message, PrivateMessage
from core.models import User, FileAttachment
from core.serializers import FileAttachmentSerializer
from core.services.encryption_utils import generate_short_id

class MessageBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBoard
        fields = ('id', 'name', 'description')

class MessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    author_avatar_url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ", read_only=True)
    attachments = FileAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'subject', 'body', 'created_at', 'author_display', 'author_avatar_url', 'attachments', 'pubkey', 'parent')

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
    decrypted_body = serializers.CharField(read_only=True, default="")
    decrypted_subject = serializers.CharField(read_only=True, default="")
    
    class Meta:
        model = PrivateMessage
        fields = ('id', 'decrypted_subject', 'decrypted_body', 'created_at', 'is_read', 'author_display', 'author_avatar_url')
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
    decrypted_body = serializers.CharField(read_only=True, default="")
    decrypted_subject = serializers.CharField(read_only=True, default="")
    
    class Meta:
        model = PrivateMessage
        fields = ('id', 'decrypted_subject', 'decrypted_body', 'created_at', 'is_read', 'recipient_display', 'recipient_avatar_url')
        read_only_fields = fields

    def get_recipient_display(self, obj):
        if obj.recipient:
             return obj.recipient.nickname if obj.recipient.nickname else obj.recipient.username
        
        if hasattr(obj, 'recipient_pubkey') and obj.recipient_pubkey:
            user = User.objects.filter(pubkey=obj.recipient_pubkey).first()
            if user:
                return user.nickname if user.nickname else user.username
            
            short_id = generate_short_id(obj.recipient_pubkey, length=8)
            return f"Moo-{short_id}"

        return 'Unknown Recipient'


    def get_recipient_avatar_url(self, obj):
        user_to_check = obj.recipient
        if not user_to_check and hasattr(obj, 'recipient_pubkey') and obj.recipient_pubkey:
            user_to_check = User.objects.filter(pubkey=obj.recipient_pubkey).first()
        
        if user_to_check and user_to_check.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user_to_check.avatar.url)
            return user_to_check.avatar.url
        return None
