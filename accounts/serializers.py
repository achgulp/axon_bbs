# Full path: axon_bbs/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import User
from accounts.identity_service import IdentityService
from accounts.avatar_generator import generate_cow_avatar
import logging

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
