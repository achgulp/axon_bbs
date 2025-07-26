# axon_bbs/api/permissions.py
from rest_framework import permissions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64
import logging
from datetime import datetime, timedelta
from django.utils import timezone

from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class TrustedPeerPermission(permissions.BasePermission):
    """
    Custom permission for trusted peers.
    - For POST requests (receive_magnet): Verifies a signature on the magnet link.
    - For GET requests (sync): Verifies a signature on a recent timestamp in the headers.
    """
    def has_permission(self, request, view):
        sender_pubkey_pem = None
        # axon_bbs/api/permissions.py
from rest_framework import permissions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import base64
import logging
from datetime import datetime, timedelta
from django.utils import timezone

from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class TrustedPeerPermission(permissions.BasePermission):
    """
    Custom permission for trusted peers.
    - For POST requests (receive_magnet): Verifies a signature on the magnet link.
    - For GET requests (sync): Verifies a signature on a recent timestamp in the headers.
    """
    def has_permission(self, request, view):
        sender_pubkey_pem = None
        
        if request.method == 'POST':
            signature_b64 = request.data.get('signature')
            sender_pubkey_pem = request.data.get('sender_pubkey')
            data_to_verify = request.data.get('magnet', '').encode()
        elif request.method == 'GET':
            signature_b64 = request.headers.get('X-Signature')
            sender_pubkey_pem = request.headers.get('X-Pubkey')
            timestamp_str = request.headers.get('X-Timestamp')
            
            if not timestamp_str:
                logger.warning("Sync request missing X-Timestamp header.")
                return False
            
            # Security: Prevent replay attacks by ensuring the timestamp is recent
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timezone.now() - timestamp > timedelta(minutes=5):
                    logger.warning(f"Sync request rejected due to old timestamp: {timestamp_str}")
                    return False
            except ValueError:
                logger.warning(f"Invalid timestamp format in sync request: {timestamp_str}")
                return False

            data_to_verify = timestamp_str.encode()
        else:
            return False

        if not all([signature_b64, sender_pubkey_pem, data_to_verify]):
            return False

        # Check if sender_pubkey is a trusted peer
        if not TrustedInstance.objects.filter(pubkey=sender_pubkey_pem).exists():
            logger.warning(f"Rejected request from untrusted public key: {sender_pubkey_pem[:30]}...")
            return False

        try:
            pubkey_obj = load_pem_public_key(sender_pubkey_pem.encode())
            signature = base64.b64decode(signature_b64)
            
            hasher = hashes.Hash(hashes.SHA256())
            hasher.update(data_to_verify)
            digest = hasher.finalize()
            
            pubkey_obj.verify(
                signature,
                digest,
                PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            # --- FIX: Corrected the f-string syntax ---
            logger.warning(f"Signature verification failed for {sender_pubkey_pem[:30]}: {str(e)}", exc_info=True)
            return False
        if request.method == 'POST':
            signature_b64 = request.data.get('signature')
            sender_pubkey_pem = request.data.get('sender_pubkey')
            data_to_verify = request.data.get('magnet', '').encode()
        elif request.method == 'GET':
            signature_b64 = request.headers.get('X-Signature')
            sender_pubkey_pem = request.headers.get('X-Pubkey')
            timestamp_str = request.headers.get('X-Timestamp')
            
            if not timestamp_str:
                logger.warning("Sync request missing X-Timestamp header.")
                return False
            
            # Security: Prevent replay attacks by ensuring the timestamp is recent
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timezone.now() - timestamp > timedelta(minutes=5):
                    logger.warning(f"Sync request rejected due to old timestamp: {timestamp_str}")
                    return False
            except ValueError:
                logger.warning(f"Invalid timestamp format in sync request: {timestamp_str}")
                return False

            data_to_verify = timestamp_str.encode()
        else:
            return False

        if not all([signature_b64, sender_pubkey_pem, data_to_verify]):
            return False

        # Check if sender_pubkey is a trusted peer
        if not TrustedInstance.objects.filter(pubkey=sender_pubkey_pem).exists():
            logger.warning(f"Rejected request from untrusted public key: {sender_pubkey_pem[:30]}...")
            return False

        try:
            pubkey_obj = load_pem_public_key(sender_pubkey_pem.encode())
            signature = base64.b64decode(signature_b64)
            
            hasher = hashes.Hash(hashes.SHA256())
            hasher.update(data_to_verify)
            digest = hasher.finalize()
            
            pubkey_obj.verify(
                signature,
                digest,
                PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            # --- FIX: Corrected the f-string syntax ---
            logger.warning(f"Signature verification failed for {sender_pubkey_pem[:30]}: {str(e)}", exc_info=True)
            return False
