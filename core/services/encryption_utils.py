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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/services/encryption_utils.py

import base64
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

def derive_key_from_password(password: str, salt: bytes, iterations: int = 100000) -> bytes:
    """Derive a 32-byte encryption key from a password and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def generate_salt() -> bytes:
    """Generate a random 16-byte salt."""
    return os.urandom(16)

def generate_checksum(data: str) -> str:
    """Generate a SHA-256 checksum of the data."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def encrypt_with_fernet(data: str, key: bytes) -> str:
    """Encrypt data using Fernet symmetric encryption."""
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_with_fernet(encrypted_data: str, key: bytes) -> str:
    """Decrypt data using Fernet symmetric encryption."""
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()

def rsa_encrypt(public_key_pem: str, data: bytes) -> bytes:
    """Encrypt data with RSA public key."""
    public_key = serialization.load_pem_public_key(public_key_pem.encode())
    return public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def rsa_decrypt(private_key_pem: str, encrypted_data: bytes) -> bytes:
    """Decrypt data with RSA private key."""
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    return private_key.decrypt(
        encrypted_data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def generate_e2e_manifest(sender_pubkey: str, recipient_pubkey: str, aes_key: bytes) -> dict:
    """Generate E2E manifest for PMs: Wrap AES key for sender and recipient."""
    checksums = {
        'sender': generate_checksum(sender_pubkey),
        'recipient': generate_checksum(recipient_pubkey)
    }
    manifest = {'encrypted_aes_keys': {}}
    for role, pubkey in [('sender', sender_pubkey), ('recipient', recipient_pubkey)]:
        encrypted_aes = rsa_encrypt(pubkey, aes_key)
        manifest['encrypted_aes_keys'][checksums[role]] = base64.b64encode(encrypted_aes).decode()
    manifest['checksums'] = checksums
    return manifest

def decrypt_for_recipients_only(e2e_manifest: dict, user_pubkey_checksum: str, user_private_key_pem: str, encrypted_content: str) -> str:
    """
    Decrypt E2E content for authorized recipients only (sender or recipient).
    Handles missing manifest gracefully.
    """
    try:
        if e2e_manifest is None:
            logger.warning("E2E manifest is missing. Cannot decrypt content. This may indicate a send failure.")
            raise ValueError("E2E manifest missing – message cannot be decrypted.")
        
        encrypted_aes_key_b64 = e2e_manifest['encrypted_aes_keys'].get(user_pubkey_checksum)
        if not encrypted_aes_key_b64:
            raise ValueError(f"No AES key found for user checksum: {user_pubkey_checksum}")
        
        # Unwrap AES key with user's private key
        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        aes_key = rsa_decrypt(user_private_key_pem, encrypted_aes_key)
        
        # Decrypt content with AES key (assuming Fernet for simplicity)
        f = Fernet(aes_key)
        return f.decrypt(base64.b64decode(encrypted_content)).decode()
    
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError(f"Failed to decrypt message: {str(e)}")

# Additional utilities (e.g., for double-encryption metadata) can go here...
def encrypt_metadata_for_peers(metadata: dict, peer_pubkeys: list) -> str:
    """Encrypt metadata for all trusted peers (placeholder for federation)."""
    # Implementation for BBS-level encryption...
    pass
