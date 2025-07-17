# axon_bbs/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import MessageBoard, Message
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_salt
import os
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model. Now also handles creation of the
    user's Nostr identity on registration.
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
            # Create a unique, encrypted file for the user's Nostr keys
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
            identity_service.generate_and_add_nostr_identity(name="default")
            logger.info(f"Successfully created initial Nostr identity for {user.username}")

        except Exception as e:
            # If identity creation fails, we should roll back the user creation
            # to prevent orphaned user accounts.
            logger.error(f"Failed to create identity for {user.username}. Rolling back user creation. Error: {e}")
            user.delete()
            # Re-raise the exception so the view returns a 500 error
            raise e

        return user


class MessageBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBoard
        fields = ('id', 'name', 'description')

class MessageSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Message
        fields = ('id', 'subject', 'body', 'author_username', 'posted_at')
        read_only_fields = ('id', 'author_username', 'posted_at')

