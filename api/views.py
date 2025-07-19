# axon_bbs/api/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import logging
import asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization, padding
import json
import base64
import requests  # Added for sharing magnets via HTTP over Tor

from .serializers import UserSerializer, MessageBoardSerializer, MessageSerializer
from core.models import MessageBoard, Message, IgnoredPubkey, BannedPubkey, TrustedInstance
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
        if 'unencrypted_priv_key' in request.session:
            del request.session['unencrypted_priv_key']
        return Response({"status": "session cleared"}, status=status.HTTP_200_OK)

class UnlockIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Decrypts the user's private key using their password and
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
            
            identity = identity_service.get_identity_by_name("default")
            if not identity:
                return Response({"error": "No default identity found for user."}, status=status.HTTP_404_NOT_FOUND)

            # Store the unencrypted key in the session
            private_key_pem = identity['private_key']
            request.session['unencrypted_priv_key'] = private_key_pem
            
            logger.info(f"Identity unlocked for user {user.username}")
            return Response({"status": "identity unlocked"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to unlock identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "Failed to unlock identity. Check password or system logs."}, status=status.HTTP_401_UNAUTHORIZED)

class ImportIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Imports an existing private key provided by the user.
        Requires the user's password to decrypt and re-encrypt the identity storage.
        """
        user = request.user
        password = request.data.get('password')
        priv_key_pem = request.data.get('priv_key_pem')
        name = request.data.get('name', 'imported')
        if not password or not priv_key_pem:
            return Response({"error": "Password and priv_key_pem are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Derive key and initialize identity service
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f:
                salt = f.read()
            encryption_key = derive_key_from_password(password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)
            
            # Add the key
            identity = identity_service.add_existing_identity(name, priv_key_pem)
            
            # Optionally set as user's pubkey if none set
            if not user.pubkey:
                user.pubkey = identity['public_key']
                user.save()

            logger.info(f"Imported identity '{name}' for user {user.username}")
            return Response({"status": "identity imported", "pubkey": identity['public_key']}, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": "Invalid priv_key_pem provided."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to import identity for {user.username}: {e}", exc_info=True)
            return Response({"error": "Failed to import identity. Check details or system logs."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MessageBoardListView(generics.ListAPIView):
    queryset = MessageBoard.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageBoardSerializer

class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        board_id = self.kwargs['pk']
        ignored_pubkeys = IgnoredPubkey.objects.filter(user=self.request.user).values_list('pubkey', flat=True)
        return Message.objects.filter(board_id=board_id).exclude(pubkey__in=ignored_pubkeys).order_by('-created_at')

class PostMessageView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        subject = request.data.get('subject')
        body = request.data.get('body')
        board_name = request.data.get('board_name', 'general')

        if not all([subject, body]):
            return Response({"error": "Subject and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the unencrypted private key from the session
        private_key_pem = request.session.get('unencrypted_priv_key')
        if not private_key_pem:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Fetch the board
            try:
                board = MessageBoard.objects.get(name=board_name)
            except MessageBoard.DoesNotExist:
                return Response({"error": f"Board '{board_name}' not found."}, status=status.HTTP_404_NOT_FOUND)

            # Construct the message content with signed nickname if set
            message_content = {
                "subject": subject,
                "body": body
            }
            if user.nickname:
                nick_hash = hashes.Hash(hashes.SHA256()).update(user.nickname.encode()).finalize()
                private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
                nick_sig = private_key.sign(
                    nick_hash,
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                    hashes.SHA256()
                )
                message_content['nickname'] = user.nickname
                message_content['nick_sig'] = base64.b64encode(nick_sig).decode()

            data = json.dumps(message_content).encode()

            # Use BitTorrentService to create and publish torrent
            if service_manager.bittorrent_service:
                magnet, torrent_file = service_manager.bittorrent_service.create_torrent(data, f"msg_{board_name}")

                # Log magnet for verification
                logger.info(f"Message torrent created: magnet={magnet}")

                # Share magnet with trusted peers via HTTP POST over Tor
                self.share_magnet_with_trusts(magnet)

                # Store locally
                Message.objects.create(
                    board=board,
                    subject=subject,
                    body=json.dumps(message_content),
                    author=user,
                    pubkey=user.pubkey,
                )

                return Response({"status": "message_published", "magnet": magnet}, status=status.HTTP_200_OK)
            else:
                logger.error("Cannot publish message, BitTorrentService is not available.")
                return Response({"error": "Cannot sync to network."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            logger.error(f"Failed to post message for {user.username}: {e}", exc_info=True)
            return Response({"error": "Could not post message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def share_magnet_with_trusts(self, magnet):
        """Share magnet to trusted peers via HTTP POST over Tor."""
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}  # Tor proxy
        trusted_urls = TrustedInstance.objects.values_list('onion_url', flat=True)
        for url in trusted_urls:
            try:
                response = requests.post(f"{url}/api/receive_magnet/", json={'magnet': magnet}, proxies=proxies)
                if response.status_code == 200:
                    logger.info(f"Magnet shared to {url}")
                else:
                    logger.warning(f"Failed to share magnet to {url}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error sharing magnet to {url}: {e}")

class ReceiveMagnetView(views.APIView):
    permission_classes = [permissions.IsAdminUser]  # Or authenticate via key

    def post(self, request, *args, **kwargs):
        magnet = request.data.get('magnet')
        if not magnet:
            return Response({"error": "Magnet required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            save_path = os.path.join(settings.BASE_DIR, 'data', 'sync')
            os.makedirs(save_path, exist_ok=True)
            my_pubkey = 'your_bbs_pubkey'  # Load from config or TrustedInstance
            decrypted = service_manager.bittorrent_service.download_and_decrypt(magnet, save_path, my_pubkey)
            # Process decrypted data (e.g., store message)
            message_content = json.loads(decrypted.decode())
            # Save to DB...
            return Response({"status": "Magnet received and processed."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to process magnet: {e}")
            return Response({"error": "Failed to process magnet."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IgnorePubkeyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        pubkey = request.data.get('pubkey')
        if not pubkey:
            return Response({"error": "Pubkey to ignore is required."}, status=status.HTTP_400_BAD_REQUEST)
        IgnoredPubkey.objects.create(user=request.user, pubkey=pubkey)
        return Response({"status": "Pubkey ignored."}, status=status.HTTP_200_OK)

class BanPubkeyView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        pubkey = request.data.get('pubkey')
        if not pubkey:
            return Response({"error": "Pubkey to ban is required."}, status=status.HTTP_400_BAD_REQUEST)
        BannedPubkey.objects.create(pubkey=pubkey)
        return Response({"status": "Pubkey banned."}, status=status.HTTP_200_OK)
