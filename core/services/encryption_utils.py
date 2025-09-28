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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/services/encryption_utils.py
import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

logger = logging.getLogger(__name__)

def generate_salt(size: int = 16) -> bytes:
    """Generates a cryptographically secure salt."""
    return os.urandom(size)

def derive_key_from_password(password: str, salt: bytes, iterations: int = 100000) -> bytes:
    """Derives a secure encryption key from a user's password and a salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_data(data: str, key: bytes) -> bytes:
    """Encrypts a string using a Fernet key."""
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """Decrypts data using a Fernet key."""
    f = Fernet(key)
    decrypted_bytes = f.decrypt(encrypted_data)
    return decrypted_bytes.decode()

def encrypt_with_public_key(data: str, public_key_pem: str) -> str:
    """Encrypts a string with an RSA public key and returns a base64 encoded string."""
    public_key = load_pem_public_key(public_key_pem.encode())
    ciphertext = public_key.encrypt(
        data.encode('utf-8'),
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(ciphertext).decode('utf-8')

def decrypt_with_private_key(encrypted_data_b64: str, private_key_pem: str) -> str:
    """Decrypts a base64 encoded string with an RSA private key."""
    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    encrypted_data = base64.b64decode(encrypted_data_b64)
    plaintext = private_key.decrypt(
        encrypted_data,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext.decode('utf-8')

def generate_short_id(pubkey_pem: str, length: int = 16) -> str:
    """Generates a semi-unique short ID from a public key PEM string."""
    hash_obj = hashlib.sha256(pubkey_pem.encode())
    return hash_obj.hexdigest()[:length]

def generate_checksum(data_string: str) -> str:
    """Generates an MD5 checksum for a given string, normalizing if it's a public key."""
    if not data_string:
        return "None"
    try:
        pubkey_obj = load_pem_public_key(data_string.encode())
        normalized_data = pubkey_obj.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8').strip().encode('utf-8')
    except Exception:
        normalized_data = data_string.strip().encode('utf-8')
    
    return hashlib.md5(normalized_data).hexdigest()

def encrypt_for_recipients_only(message: str, pubkeys: list):
    """
    Encrypts a message with a session key, then encrypts the session key
    for a list of recipient public keys. Returns the encrypted message
    and the list of encrypted session keys.
    """
    aes_key = os.urandom(32)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    padder = PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(message.encode('utf-8')) + padder.finalize()
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    encrypted_keys = {}
    for pubkey_pem in pubkeys:
        try:
            pubkey_obj = serialization.load_pem_public_key(pubkey_pem.encode())
            encrypted_key = pubkey_obj.encrypt(
                aes_key,
                rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            # MODIFIED: Normalize the public key before generating the checksum
            normalized_pubkey = pubkey_obj.public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            checksum = generate_checksum(normalized_pubkey)
            encrypted_keys[checksum] = base64.b64encode(encrypted_key).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt session key for pubkey with checksum {generate_checksum(pubkey_pem)}: {e}")

    return encrypted_data, {
        "encryption_iv": base64.b64encode(iv).decode('utf-8'),
        "encrypted_aes_keys": encrypted_keys,
    }

def decrypt_for_recipients_only(e2e_content: bytes, e2e_manifest: dict, private_key_pem: str) -> str | None:
    """
    Decrypts the E2E content using a key from the metadata manifest.
    """
    try:
        private_key = load_pem_private_key(private_key_pem.encode(), password=None)
        public_key = private_key.public_key()
        user_checksum = generate_checksum(public_key.public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8'))
        
        encrypted_aes_key_b64 = e2e_manifest['encrypted_aes_keys'].get(user_checksum)

        if not encrypted_aes_key_b64:
            logger.warning("Could not find an encryption envelope for this user's key in the E2E manifest.")
            return None
        
        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        
        iv = base64.b64decode(e2e_manifest['encryption_iv'])
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(e2e_content) + decryptor.finalize()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(padded_data) + unpadder.finalize()
        
        return decrypted_data.decode('utf-8')
    
    except Exception as e:
        logger.error(f"Failed to decrypt E2E content: {e}", exc_info=True)
        return None
