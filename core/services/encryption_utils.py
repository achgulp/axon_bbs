# axon_bbs/core/services/encryption_utils.py
import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hashlib  # Added for short ID

logger = logging.getLogger(__name__)

def generate_salt(size: int = 16) -> bytes:
    """
    Generates a cryptographically secure salt.
    """
    return os.urandom(size)

def derive_key_from_password(password: str, salt: bytes, iterations: int = 100000) -> bytes:
    """
    Derives a secure encryption key from a user's password and a salt
    using PBKDF2HMAC.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    # The key must be base64-encoded to be used by Fernet
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_data(data: str, key: bytes) -> bytes:
    """
    Encrypts a string using a Fernet key.
    """
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """
    Decrypts data using a Fernet key.
    Returns the decrypted data as a string.
    """
    f = Fernet(key)
    decrypted_bytes = f.decrypt(encrypted_data)
    return decrypted_bytes.decode()

def generate_short_id(pubkey_pem: str, length: int = 16) -> str:
    """
    Generates a semi-unique short ID from a public key PEM string.
    """
    hash_obj = hashlib.sha256(pubkey_pem.encode())
    return hash_obj.hexdigest()[:length]
