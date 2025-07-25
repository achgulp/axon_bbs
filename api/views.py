# axon_bbs/api/views.py
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import logging
import asyncio
import threading
import traceback # Import traceback for detailed error logging
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
import json
import base64
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import timedelta
from django.utils import timezone
from django.apps import apps

from .serializers import UserSerializer, MessageBoardSerializer, MessageSerializer, ContentExtensionRequestSerializer
from .permissions import TrustedPeerPermission
from core.models import MessageBoard, Message, IgnoredPubkey, BannedPubkey, TrustedInstance, Alias, ContentExtensionRequest
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
        if 'unencrypted_priv_key' in request.session:
            del request.session['unencrypted_priv_key']
        return Response({"status": "session cleared"}, status=status.HTTP_200_OK)

class UnlockIdentityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        password = request.data.get('password')
        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
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
        user = request.user
        password = request.data.get('password')
        priv_key_pem = request.data.get('priv_key_pem')
        name = request.data.get('name', 'imported')
        if not password or not priv_key_pem:
            return Response({"error": "Password and priv_key_pem are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', user.username)
            salt_path = os.path.join(user_data_dir, 'salt.bin')
            with open(salt_path, 'rb') as f:
                salt = f.read()
            encryption_key = derive_key_from_password(password, salt)
            identity_storage_path = os.path.join(user_data_dir, 'identities.dat')
            identity_service = IdentityService(identity_storage_path, encryption_key)
            identity = identity_service.add_existing_identity(name, priv_key_pem)
            if not user.pubkey:
                user.pubkey = identity['public_key']
                user.save()
            logger.info(f"Imported identity '{name}' for user {user.username}")
            return Response({"status": "identity imported", "pubkey": identity['public_key']}, status=status.HTTP_200_OK)
        except ValueError:
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
        private_key_pem = request.session.get('unencrypted_priv_key')
        if not private_key_pem:
            return Response({"error": "identity_locked"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            try:
                board = MessageBoard.objects.get(name=board_name)
            except MessageBoard.DoesNotExist:
                return Response({"error": f"Board '{board_name}' not found."}, status=status.HTTP_404_NOT_FOUND)
            message_content = {
                "subject": subject, "body": body, "board": board.name, "pubkey": user.pubkey
            }
            if user.nickname:
                nick_hash = hashes.Hash(hashes.SHA256())
                nick_hash.update(user.nickname.encode())
                digest = nick_hash.finalize()
                private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
                nick_sig = private_key.sign(
                    digest, PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH), hashes.SHA256()
                )
                message_content['nickname'] = user.nickname
                message_content['nick_sig'] = base64.b64encode(nick_sig).decode()
            data = json.dumps(message_content).encode()
            if service_manager.bittorrent_service:
                magnet, torrent_file = service_manager.bittorrent_service.create_torrent(data, f"msg_{board_name}")
                logger.info(f"Message torrent created: magnet={magnet}")
                thread = threading.Thread(target=self.share_magnet_with_trusts, args=(magnet,))
                thread.daemon = True
                thread.start()
                Message.objects.create(
                    board=board, subject=subject, body=body, author=user, pubkey=user.pubkey,
                )
                return Response({"status": "message_published", "magnet": magnet}, status=status.HTTP_200_OK)
            else:
                logger.error("Cannot publish message, BitTorrentService is not available.")
                return Response({"error": "Cannot sync to network."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Failed to post message for {user.username}: {e}", exc_info=True)
            return Response({"error": "Could not post message."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def share_magnet_with_trusts(self, magnet):
        private_key = service_manager.bittorrent_service.get_private_key()
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        if not private_key or not local_instance:
            logger.error("BACKGROUND: Could not find local instance or its private key to sign magnet sharing request.")
            return
        local_pubkey = local_instance.pubkey
        local_p2p_address = local_instance.p2p_onion_address
        
        hash_ctx = hashes.Hash(hashes.SHA256())
        hash_ctx.update(magnet.encode())
        digest = hash_ctx.finalize()
        signature = private_key.sign(
            digest, PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH), hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature).decode()
        payload = {
            'magnet': magnet, 
            'signature': signature_b64, 
            'sender_pubkey': local_pubkey,
            'sender_p2p_address': local_p2p_address
        }
        
        trusted_peers = TrustedInstance.objects.exclude(pk=local_instance.pk)
        for peer in trusted_peers:
            url = peer.web_ui_onion_url
            if not url: continue
            
            proxies = {}
            if '.onion' in url:
                proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

            try:
                target_url = url.strip('/') + '/api/receive_magnet/'
                response = requests.post(target_url, json=payload, proxies=proxies, timeout=30)
                if response.status_code == 200:
                    logger.info(f"BACKGROUND: Magnet shared to {url}")
                else:
                    logger.warning(f"BACKGROUND: Failed to share magnet to {url}: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException:
                logger.error(f"BACKGROUND: A critical network error occurred while sharing magnet to {url}.")
                logger.error(traceback.format_exc())

@method_decorator(csrf_exempt, name='dispatch')
class ReceiveMagnetView(views.APIView):
    permission_classes = [TrustedPeerPermission]

    def post(self, request, *args, **kwargs):
        magnet = request.data.get('magnet')
        peer_p2p_address = request.data.get('sender_p2p_address')

        if not magnet:
            return Response({"error": "Magnet required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            save_path = os.path.join(settings.BASE_DIR, 'data', 'sync')
            os.makedirs(save_path, exist_ok=True)
            local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
            if not local_instance:
                 return Response({"error": "Local instance not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            my_pubkey = local_instance.pubkey
            
            handle, decrypted_content = service_manager.bittorrent_service.download_and_decrypt(
                magnet, save_path, my_pubkey, peer_address=peer_p2p_address
            )
            
            if not decrypted_content:
                return Response({"error": "Failed to decrypt content, envelope may not be for this instance."}, status=status.HTTP_403_FORBIDDEN)
            content = json.loads(decrypted_content.decode())
            subject = content.get('subject')
            body = content.get('body')
            pubkey = content.get('pubkey')
            board_name = content.get('board', 'general')
            nickname = content.get('nickname')
            nick_sig = content.get('nick_sig')
            board, _ = MessageBoard.objects.get_or_create(name=board_name, defaults={'description': 'Auto-created board'})
            Message.objects.create(
                board=board, subject=subject, body=body, pubkey=pubkey,
            )
            if nickname and nick_sig and pubkey:
                try:
                    pubkey_obj = serialization.load_pem_public_key(pubkey.encode())
                    nick_hash = hashes.Hash(hashes.SHA256())
                    nick_hash.update(nickname.encode())
                    digest = nick_hash.finalize()
                    pubkey_obj.verify(
                        base64.b64decode(nick_sig), digest, PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH), hashes.SHA256()
                    )
                    Alias.objects.update_or_create(
                        pubkey=pubkey, defaults={'nickname': nickname, 'verified': True}
                    )
                    logger.info(f"Verified and stored alias for pubkey {pubkey[:12]}...: {nickname}")
                except Exception as e:
                    logger.warning(f"Failed to verify nickname sig for pubkey {pubkey[:12]}...: {e}")
            new_magnet = service_manager.bittorrent_service.re_envelope_and_reseed(handle, save_path, my_pubkey)
            if new_magnet:
                logger.info(f"Re-enveloped and re-seeding torrent. New magnet: {new_magnet}")
                thread = threading.Thread(target=PostMessageView.share_magnet_with_trusts, args=(self, new_magnet,))
                thread.daemon = True
                thread.start()
            return Response({"status": "Magnet received and processed."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to process magnet: {e}", exc_info=True)
            return Response({"error": "Failed to process magnet."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IgnorePubkeyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        pubkey = request.data.get('pubkey')
        if not pubkey:
            return Response({"error": "Pubkey to ignore is required."}, status=status.HTTP_400_BAD_REQUEST)
        IgnoredPubkey.objects.get_or_create(user=request.user, pubkey=pubkey)
        return Response({"status": "Pubkey ignored."}, status=status.HTTP_200_OK)

class BanPubkeyView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        pubkey = request.data.get('pubkey')
        is_temporary = request.data.get('is_temporary', False)
        duration_hours = request.data.get('duration_hours')
        if not pubkey:
            return Response({"error": "Pubkey to ban is required."}, status=status.HTTP_400_BAD_REQUEST)
        expires_at = None
        if is_temporary:
            if not duration_hours:
                return Response({"error": "Duration in hours is required for a temporary ban."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                expires_at = timezone.now() + timedelta(hours=int(duration_hours))
            except (ValueError, TypeError):
                return Response({"error": "Invalid duration format."}, status=status.HTTP_400_BAD_REQUEST)
        ban, created = BannedPubkey.objects.update_or_create(
            pubkey=pubkey, defaults={'is_temporary': is_temporary, 'expires_at': expires_at}
        )
        status_msg = "Pubkey permanently banned."
        if is_temporary:
            status_msg = f"Pubkey temporarily banned until {expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')}."
        return Response({"status": status_msg}, status=status.HTTP_200_OK)

class RequestContentExtensionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        content_id = request.data.get('content_id')
        content_type = request.data.get('content_type')
        if not all([content_id, content_type]):
            return Response({"error": "content_id and content_type are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            model = apps.get_model('core', content_type.capitalize())
            content_obj = model.objects.get(pk=content_id, author=request.user)
        except (LookupError, model.DoesNotExist):
            return Response({"error": "Invalid content_type or content not found/not owned by user."}, status=status.HTTP_404_NOT_FOUND)
        ext_request, created = ContentExtensionRequest.objects.get_or_create(
            content_id=content_id, user=request.user, defaults={'content_type': content_type}
        )
        if not created and ext_request.status in ['pending', 'approved']:
             return Response({"status": "An extension request is already pending or has been approved."}, status=status.HTTP_200_OK)
        ext_request.status = 'pending'
        ext_request.save()
        return Response(ContentExtensionRequestSerializer(ext_request).data, status=status.HTTP_201_CREATED)

class ReviewContentExtensionView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk, *args, **kwargs):
        try:
            ext_request = ContentExtensionRequest.objects.get(pk=pk, status='pending')
        except ContentExtensionRequest.DoesNotExist:
            return Response({"error": "Request not found or already reviewed."}, status=status.HTTP_404_NOT_FOUND)
        action = request.data.get('action')
        if action not in ['approve', 'deny']:
            return Response({"error": "Action must be 'approve' or 'deny'."}, status=status.HTTP_400_BAD_REQUEST)
        ext_request.status = f"{action}d"
        ext_request.reviewed_by = request.user
        ext_request.reviewed_at = timezone.now()
        if action == 'approve':
            try:
                model = apps.get_model('core', ext_request.content_type.capitalize())
                content_obj = model.objects.get(pk=ext_request.content_id)
                content_obj.expires_at += timedelta(days=30)
                content_obj.save()
            except (LookupError, model.DoesNotExist):
                ext_request.status = 'denied'
                logger.error(f"Could not find content {ext_request.content_id} to approve extension.")
        ext_request.save()
        return Response(ContentExtensionRequestSerializer(ext_request).data, status=status.HTTP_200_OK)

class UnpinContentView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        content_id = request.data.get('content_id')
        content_type = request.data.get('content_type')
        if not all([content_id, content_type]):
            return Response({"error": "content_id and content_type are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            model = apps.get_model('core', content_type.capitalize())
            content_obj = model.objects.get(pk=content_id)
        except (LookupError, model.DoesNotExist):
            return Response({"error": "Content not found."}, status=status.HTTP_404_NOT_FOUND)
        if content_obj.pinned_by and content_obj.pinned_by.is_staff and not request.user.is_staff:
             return Response({"error": "Moderators cannot unpin content pinned by an Admin."}, status=status.HTTP_403_FORBIDDEN)
        content_obj.is_pinned = False
        content_obj.pinned_by = None
        content_obj.save()
        return Response({"status": "Content unpinned successfully."}, status=status.HTTP_200_OK)
