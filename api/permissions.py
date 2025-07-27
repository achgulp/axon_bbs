# Full path: axon_bbs/api/permissions.py
from rest_framework import permissions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import base64
import logging
from datetime import datetime, timedelta
from django.utils import timezone

from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

class TrustedPeerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        sender_pubkey_pem = None
        
        if request.method == 'POST':
            signature_b64 = request.data.get('signature')
            sender_pubkey_pem = request.data.get('sender_pubkey')
            data_to_verify = request.data.get('magnet', '').encode()
        elif request.method == 'GET':
            signature_b64 = request.headers.get('X-Signature')
            sender_pubkey_pem_b64 = request.headers.get('X-Pubkey')
            if sender_pubkey_pem_b64:
                try:
                    sender_pubkey_pem = base64.b64decode(sender_pubkey_pem_b64).decode()
                    logger.debug(f"Decoded raw sender_pubkey_pem (length: {len(sender_pubkey_pem)}): checksum {generate_checksum(sender_pubkey_pem)}")
                except Exception as e:
                    logger.warning(f"Failed to base64 decode X-Pubkey: {e}")
                    return False
            timestamp_str = request.headers.get('X-Timestamp')
            if not timestamp_str: return False
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timezone.now() - timestamp > timedelta(minutes=5): return False
            except ValueError: return False
            data_to_verify = timestamp_str.encode()
        else:
            return False

        if not all([signature_b64, sender_pubkey_pem, data_to_verify]):
            logger.warning("Missing required fields for permission check: signature, pubkey, or data_to_verify")
            return False

        # Log raw incoming pubkey checksum
        raw_checksum = generate_checksum(sender_pubkey_pem)
        logger.info(f"Incoming raw pubkey checksum: {raw_checksum}")

        # Normalize the incoming public key by loading and re-serializing
        try:
            pubkey_obj = load_pem_public_key(sender_pubkey_pem.strip().encode())
            cleaned_sender_pubkey = pubkey_obj.public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8').strip()
            normalized_checksum = generate_checksum(cleaned_sender_pubkey)
            if raw_checksum != normalized_checksum:
                logger.info(f"Pubkey normalized; original checksum {raw_checksum} -> normalized {normalized_checksum}")
        except Exception as e:
            logger.warning(f"Failed to normalize incoming public key: {e}")
            return False
        
        # Log expected pubkeys from DB for comparison
        expected_checksums = [generate_checksum(inst.pubkey) for inst in TrustedInstance.objects.exclude(encrypted_private_key__isnull=False) if inst.pubkey]
        logger.info(f"Expected trusted peer checksums: {', '.join(expected_checksums) or 'None'}")
        
        # --- FINAL FIX: Query for the specific peer key, excluding our own identity ---
        if not TrustedInstance.objects.filter(pubkey=cleaned_sender_pubkey).exclude(encrypted_private_key__isnull=False).exists():
            incoming_checksum = generate_checksum(cleaned_sender_pubkey)
            logger.warning(f"Rejected request from untrusted or self-identifying public key with checksum: {incoming_checksum}. Expected: {', '.join(expected_checksums) or 'None'}")
            return False
        # --- END FIX ---

        try:
            pubkey_obj = load_pem_public_key(cleaned_sender_pubkey.encode())
            signature = base64.b64decode(signature_b64)
            hasher = hashes.Hash(hashes.SHA256())
            hasher.update(data_to_verify)
            digest = hasher.finalize()
            pubkey_obj.verify(signature, digest, PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH), hashes.SHA256())
            logger.debug(f"Signature verification successful for pubkey checksum: {generate_checksum(cleaned_sender_pubkey)}")
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed for {cleaned_sender_pubkey[:30]}: {str(e)}", exc_info=True)
            return False
