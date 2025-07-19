# axon_bbs/api/permissions.py
from rest_framework import permissions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64
import logging
from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class HasBoardAccess(permissions.BasePermission):
    """
    Custom permission to only allow users with the correct
    access level to see a message board.
    
    (This is a placeholder for a real permission system)
    """
    def has_object_permission(self, request, view, obj):
        # For now, we'll allow any authenticated user to see any board.
        # A real implementation would check obj.required_access_level
        # against the request.user.access_level.
        return request.user and request.user.is_authenticated

class HasFileAreaViewAccess(permissions.BasePermission):
    """
    Custom permission for viewing files in a FileArea.
    (Placeholder)
    """
    def has_object_permission(self, request, view, obj):
        # Similar to boards, allow any authenticated user for now.
        return request.user and request.user.is_authenticated

class HasFileAreaUploadAccess(permissions.BasePermission):
    """
    Custom permission for uploading files to a FileArea.
    (Placeholder)
    """
    def has_object_permission(self, request, view, obj):
        # Similar to boards, allow any authenticated user for now.
        return request.user and request.user.is_authenticated


class TrustedPeerPermission(permissions.BasePermission):
    """
    Custom permission for trusted peers to access receive_magnet endpoint.
    Verifies a signature on the magnet using the sender's pubkey, which must be in TrustedInstance.
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            return False

        magnet = request.data.get('magnet')
        signature_b64 = request.data.get('signature')
        sender_pubkey = request.data.get('sender_pubkey')

        if not all([magnet, signature_b64, sender_pubkey]):
            return False

        # Check if sender_pubkey is trusted
        if not TrustedInstance.objects.filter(pubkey=sender_pubkey).exists():
            return False

        try:
            pubkey_obj = load_pem_public_key(sender_pubkey.encode())
            signature = base64.b64decode(signature_b64)
            hash_ctx = hashes.Hash(hashes.SHA256())
            hash_ctx.update(magnet.encode())
            digest = hash_ctx.finalize()
            pubkey_obj.verify(
                signature,
                digest,
                PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False
