# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/federation/permissions.py
from rest_framework import permissions
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
import base64
import logging
from datetime import datetime, timedelta, timezone

from django.utils import timezone as django_timezone

from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

class TrustedPeerPermission(permissions.BasePermission):
    """
    Custom permission to only allow requests from trusted peer instances.
    - Verifies the sender's public key is in the local TrustedInstance table.
    - Verifies the request signature to prove ownership of the key.
    - Attaches the peer's TrustedInstance object to the request.
    """
    def has_permission(self, request, view):
        sender_pubkey_pem = None
        signature_b64 = None
        data_to_verify = None

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
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                if abs(django_timezone.now() - timestamp) > timedelta(minutes=5):
                    logger.warning("Request rejected due to expired timestamp.")
                    return False
            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_str}")
                return False
            data_to_verify = timestamp_str.encode('utf-8')

        elif request.method == 'POST':
            signature_b64 = request.data.get('signature')
            sender_pubkey_pem = request.data.get('sender_pubkey')
            data_to_verify = request.data.get('content_hash', '').encode('utf-8')
        
        else:
            return False

        if not all([signature_b64, sender_pubkey_pem, data_to_verify is not None]):
            logger.warning("Missing required fields for permission check: signature, pubkey, or data_to_verify.")
            return False

        try:
            pubkey_obj = load_pem_public_key(sender_pubkey_pem.strip().encode('utf-8'))
            cleaned_sender_pubkey = pubkey_obj.public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8').strip()
        except Exception as e:
            logger.warning(f"Failed to parse/normalize incoming public key: {e}")
            return False
        
        try:
            peer_instance = TrustedInstance.objects.get(pubkey=cleaned_sender_pubkey, is_trusted_peer=True)
            request.peer_instance = peer_instance
        except TrustedInstance.DoesNotExist:
            incoming_checksum = generate_checksum(cleaned_sender_pubkey)
            logger.warning(f"REJECTED request from untrusted public key with checksum: {incoming_checksum}. This key was not found in the list of trusted peers.")
            return False
        
        logger.info(f"Pubkey with checksum {generate_checksum(cleaned_sender_pubkey)} is trusted. Proceeding to signature verification.")

        try:
            signature = base64.b64decode(signature_b64)
            if request.method == 'GET':
                hasher = hashes.Hash(hashes.SHA256())
                hasher.update(data_to_verify)
                digest = hasher.finalize()
            else:
                digest = data_to_verify
            
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

class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow moderators or admins (staff).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_moderator or request.user.is_staff
