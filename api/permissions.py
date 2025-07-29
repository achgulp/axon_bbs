# Full path: axon_bbs/api/permissions.py
from rest_framework import permissions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
import base64
import logging
from datetime import datetime, timedelta, timezone

from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

class TrustedPeerPermission(permissions.BasePermission):
    """
    Custom permission to only allow requests from trusted peer instances.
    - Verifies the sender's public key is in the local TrustedInstance table.
    - Verifies the request signature to prove ownership of the key.
    """
    def has_permission(self, request, view):
        sender_pubkey_pem = None
        signature_b64 = None
        data_to_verify = None

        # Extract details based on request method
        if request.method == 'GET':
            signature_b64 = request.headers.get('X-Signature')
            sender_pubkey_pem_b64 = request.headers.get('X-Pubkey')
            if sender_pubkey_pem_b64:
                try:
                    sender_pubkey_pem = base64.b64decode(sender_pubkey_pem_b64).decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to base64 decode X-Pubkey header: {e}")
                    return False
            timestamp_str = request.headers.get('X-Timestamp')
            if not timestamp_str:
                logger.warning("Missing X-Timestamp header for GET request.")
                return False
            try:
                # Ensure timestamp is timezone-aware for comparison
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc) # Assume UTC if not specified
                if abs(timezone.now() - timestamp) > timedelta(minutes=5):
                    logger.warning("Request rejected due to expired timestamp.")
                    return False
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}")
                return False
            data_to_verify = timestamp_str.encode('utf-8')

        elif request.method == 'POST':
            signature_b64 = request.data.get('signature')
            sender_pubkey_pem = request.data.get('sender_pubkey')
            data_to_verify = request.data.get('magnet', '').encode('utf-8')
        
        else:
            return False # Reject other methods

        if not all([signature_b64, sender_pubkey_pem, data_to_verify is not None]):
            logger.warning("Missing required fields for permission check: signature, pubkey, or data_to_verify.")
            return False

        # Normalize the incoming public key to ensure a consistent format
        try:
            pubkey_obj = load_pem_public_key(sender_pubkey_pem.strip().encode('utf-8'))
            cleaned_sender_pubkey = pubkey_obj.public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8').strip()
        except Exception as e:
            logger.warning(f"Failed to parse/normalize incoming public key: {e}")
            return False
        
        # --- VERIFICATION STEP 1: Check if the sender is a trusted peer ---
        # This query is the most critical part for fixing the 401 error.
        trusted_peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        
        # Create a list of trusted pubkeys for comparison
        trusted_pubkeys = [p.pubkey for p in trusted_peers if p.pubkey]
        
        # Log for diagnostics
        expected_checksums = [generate_checksum(key) for key in trusted_pubkeys]
        logger.info(f"Permission check: Found {len(expected_checksums)} trusted peer checksum(s) in DB: {', '.join(expected_checksums) or 'None'}")

        if cleaned_sender_pubkey not in trusted_pubkeys:
            incoming_checksum = generate_checksum(cleaned_sender_pubkey)
            logger.warning(f"REJECTED request from untrusted public key with checksum: {incoming_checksum}. This key was not found in the list of trusted peers.")
            return False
        
        logger.info(f"Pubkey with checksum {generate_checksum(cleaned_sender_pubkey)} is trusted. Proceeding to signature verification.")

        # --- VERIFICATION STEP 2: Verify the signature ---
        try:
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
            logger.debug(f"Signature verification successful for pubkey checksum: {generate_checksum(cleaned_sender_pubkey)}")
            return True
        except Exception as e:
            logger.warning(f"Signature verification FAILED for pubkey {generate_checksum(cleaned_sender_pubkey)}: {e}", exc_info=True)
            return False

