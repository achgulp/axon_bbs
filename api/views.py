# axon_bbs/api/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import logging
import asyncio
from pynostr.key import PrivateKey
from pynostr.event import Event
import json

from .serializers import UserSerializer, MessageBoardSerializer
from core.models import MessageBoard, IgnoredUser
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)
User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Clears the decrypted private key from the server's session memory.
        """
        if 'unencrypted_nostr_pk' in request.session:
            del request.session['unencrypted_nostr_pk']
        return Response({"status": "session cleared"}, status=status.HTTP_200_OK)

class UnlockIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Decrypts the user's Nostr private key using their password and
        stores it in the server-side session for later use.
        """
        user = request.user
        password = request.data.get('password')
        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Derive key and initialize identity service
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f:
                salt = f.read()
            encryption_key = derive_key_from_password(password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)
            
            nostr_identity = identity_service.get_identity_by_name("default")
            if not nostr_identity:
                return Response({"error": "No default Nostr identity found for user."}, status=status.HTTP_404_NOT_FOUND)

            # Store the unencrypted key in the session
            private_key_hex = nostr_identity['private_key']
            request.session['unencrypted_nostr_pk'] = private_key_hex
            
            logger.info(f"Identity unlocked for user {user.username}")
            return Response({"status": "identity unlocked"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to unlock identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "Failed to unlock identity. Check password or system logs."}, status=status.HTTP_401_UNAUTHORIZED)


class MessageBoardListView(generics.ListAPIView):
    queryset = MessageBoard.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageBoardSerializer

class PostNostrMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        subject = request.data.get('subject')
        body = request.data.get('body')
        board_name = request.data.get('board_name', 'general')

        if not all([subject, body]):
            return Response({"error": "Subject and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the unencrypted private key from the session
        private_key_hex = request.session.get('unencrypted_nostr_pk')
        if not private_key_hex:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Fetch the board to get its specific relays
            try:
                board = MessageBoard.objects.get(name=board_name)
                relays = board.relays if board.relays else settings.NOSTR_RELAY_URLS
            except MessageBoard.DoesNotExist:
                return Response({"error": f"Board '{board_name}' not found."}, status=status.HTTP_404_NOT_FOUND)

            # Construct the message content
            message_content = {
                "subject": subject,
                "body": body
            }

            # Construct and sign the event using the in-memory key
            private_key = PrivateKey.from_hex(private_key_hex)
            event = Event(
                content=json.dumps(message_content),
                tags=[["t", board_name]]
            )
            event.sign(private_key.hex())
            
            logger.info(f"Event created with session key: id={event.id}")

            # Publish the event to the board's relays (or global fallback)
            if service_manager.nostr_service and service_manager.loop:
                future = asyncio.run_coroutine_threadsafe(
                    service_manager.nostr_service.publish_event(event, relays=relays),
                    service_manager.loop
                )
                publish_success = future.result()  # Now returns True/False
                if publish_success:
                    logger.info(f"Event {event.id} published by user {user.username} to relays: {', '.join(relays)}")
                    return Response({"status": "message_published", "event_id": event.id, "relays": relays}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Could not post message to any relays. Check logs for details."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            else:
                logger.error("Cannot publish event, NostrService or its event loop is not available.")
                return Response({"error": "Cannot connect to the Nostr network."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            logger.error(f"Failed to post Nostr message for {user.username}: {e}", exc_info=True)
            return Response({"error": "Could not post message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IgnoreUserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_to_ignore_username = request.data.get('username')
        if not user_to_ignore_username:
            return Response({"error": "Username to ignore is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_to_ignore = User.objects.get(username=user_to_ignore_username)
            IgnoredUser.objects.create(user=request.user, ignored_user=user_to_ignore)
            return Response({"status": f"User {user_to_ignore_username} has been ignored."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User to ignore not found."}, status=status.HTTP_404_NOT_FOUND)

class BanUserView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        user_to_ban_username = request.data.get('username')
        if not user_to_ban_username:
            return Response({"error": "Username to ban is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_to_ban = User.objects.get(username=user_to_ban_username)
            user_to_ban.is_banned = True
            user_to_ban.save()
            return Response({"status": f"User {user_to_ban_username} has been banned."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User to ban not found."}, status=status.HTTP_404_NOT_FOUND)
