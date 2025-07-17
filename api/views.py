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

from .serializers import UserSerializer, MessageBoardSerializer
from core.models import MessageBoard
from core.services.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password
from core.services.service_manager import service_manager

logger = logging.getLogger(__name__)
User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class MessageBoardListView(generics.ListAPIView):
    queryset = MessageBoard.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageBoardSerializer

class PostNostrMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        password = request.data.get('password')
        subject = request.data.get('subject')
        body = request.data.get('body')
        board_name = request.data.get('board_name', 'general')

        if not all([password, subject, body]):
            return Response({"error": "Password, subject, and body are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Unlock Identity Service
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

            private_key_hex = nostr_identity['private_key']
            
            # 2. Construct and sign the event using pynostr
            private_key = PrivateKey.from_hex(private_key_hex)
            event = Event(
                content=f"Subject: {subject}\n\n{body}",
                tags=[["t", board_name]]
            )
            event.sign(private_key.hex())
            
            # Add logging to debug event
            logger.info(f"Event created: id={event.id}, pubkey={event.pubkey}, sig={event.sig}, kind={event.kind}, created_at={event.created_at}, content='{event.content[:50]}...', tags={event.tags}")

            # 3. Publish the event
            if service_manager.nostr_service and service_manager.loop:
                future = asyncio.run_coroutine_threadsafe(
                    service_manager.nostr_service.publish_event(event),
                    service_manager.loop
                )
                # Wait for the coroutine to complete
                try:
                    future.result()
                    logger.info(f"Event {event.id} published by user {user.username}")
                    return Response({"status": "message_published", "event_id": event.id}, status=status.HTTP_200_OK)
                except Exception as pub_err:
                    logger.error(f"Failed to publish event: {pub_err}", exc_info=True)
                    return Response({"error": f"Failed to publish event: {str(pub_err)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                logger.error("Cannot publish event, NostrService or its event loop is not available.")
                return Response({"error": "Cannot connect to the Nostr network."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            logger.error(f"Failed to post Nostr message for {user.username}: {e}", exc_info=True)
            return Response({"error": "Failed to post message. Please check your password or system logs."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
