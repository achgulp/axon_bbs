# axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message, Alias, User
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_salt, generate_short_id
import os
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model. Now also handles creation of the
    user's identity on registration.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password')

    def create(self, validated_data):
        """
        Overrides the default create method to add identity creation.
        """
        # 1. Create the standard Django user
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )
        logger.info(f"Created new Django user: {user.username}")

        try:
            # 2. Prepare for identity creation
            # Create a unique, encrypted file for the user's keys
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            os.makedirs(user_data_dir, exist_ok=True)
            
            # Generate and save a unique salt for this user
            salt = generate_salt()
            with open(os.path.join(user_data_dir, 'salt.bin'), 'wb') as f:
                f.write(salt)

            # Derive an encryption key from their password
            encryption_key = derive_key_from_password(validated_data['password'], salt)

            # 3. Create the user's identity service and generate keys
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
            # If identity creation fails, roll back user creation
            logger.error(f"Failed to create identity for {user.username}. Rolling back user creation. Error: {e}")
            user.delete()
            raise e

        return user


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
        if obj.author:
            return obj.author.nickname if obj.author.nickname else obj.author.username
        elif obj.pubkey:
            alias = Alias.objects.filter(pubkey=obj.pubkey, verified=True).first()
            if alias:
                # Check for nickname conflicts with other aliases or local users
                conflicting = Alias.objects.filter(nickname=alias.nickname).exclude(pubkey=obj.pubkey).exists() or \
                              User.objects.filter(nickname=alias.nickname).exists()
                if conflicting:
                    short_id = generate_short_id(obj.pubkey)
                    return f"{alias.nickname} {short_id}"
                return alias.nickname
            else:
                short_id = generate_short_id(obj.pubkey)
                return f"Moo {short_id}"
        return 'Anonymous'
