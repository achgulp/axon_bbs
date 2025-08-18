# Full path: axon_bbs/core/services/bitsync_service.py
import os
import json
import hashlib
import logging
import base64
from typing import List, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from django.conf import settings
from django.db.models import Q
from core.models import TrustedInstance, User
from .encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

CHUNK_SIZE = 256 * 1024

class BitSyncService:
    def __init__(self):
        self.chunk_storage_path = os.path.join(settings.BASE_DIR, 'data', 'bitsync_chunks')
        os.makedirs(self.chunk_storage_path, exist_ok=True)
        logger.info("BitSyncService initialized. Chunk storage is at: %s", self.chunk_storage_path)

    # UPDATED: The missing function has been restored.
    def are_all_chunks_local(self, manifest: dict) -> bool:
        """
        Checks the local disk to see if all chunks for a given manifest exist.
        :param manifest: The content manifest dictionary.
        :return: True if all chunks are present, False otherwise.
        """
        if not manifest or 'chunk_hashes' not in manifest:
            return False
        
        content_hash = manifest.get('content_hash')
        num_chunks = len(manifest.get('chunk_hashes', []))
        
        for i in range(num_chunks):
            chunk_path = self.get_chunk_path(content_hash, i)
            if not os.path.exists(chunk_path):
                return False # A chunk is missing
        
        return True # All chunks were found

    def _load_local_private_key(self):
        """Loads and decrypts the local instance's private key."""
        try:
            local_instance = TrustedInstance.objects.get(encrypted_private_key__isnull=False, is_trusted_peer=False)
            if local_instance.encrypted_private_key:
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                f = Fernet(key)
                decrypted_pem = f.decrypt(local_instance.encrypted_private_key.encode())
                return serialization.load_pem_private_key(decrypted_pem, password=None)
        except Exception as e:
            logger.error(f"Failed to load or decrypt local private key: {e}")
            return None

    def get_decrypted_aes_key(self, manifest: dict):
        """Recovers the original AES key from a manifest using the local private key."""
        private_key = self._load_local_private_key()
        if not private_key:
            raise ValueError("Could not load local private key to decrypt manifest.")

        local_instance_pubkey = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        local_checksum = generate_checksum(local_instance_pubkey)
        encrypted_aes_key_b64 = manifest['encrypted_aes_keys'].get(local_checksum)

        if not encrypted_aes_key_b64:
            raise ValueError("Manifest does not contain an encryption envelope for the local instance.")

        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        return private_key.decrypt(
            encrypted_aes_key,
            rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )

    def rekey_manifest_for_new_peers(self, manifest: dict):
        """
        Takes an existing manifest, decrypts its AES key, and adds new encryption
        envelopes for any trusted peers who are not already recipients.
        """
        original_aes_key = self.get_decrypted_aes_key(manifest)
        if not original_aes_key:
            raise ValueError("Failed to obtain original AES key from manifest.")

        all_peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        existing_checksums = manifest['encrypted_aes_keys'].keys()
        
        updated = False
        for peer in all_peers:
            peer_checksum = generate_checksum(peer.pubkey)
            if peer_checksum not in existing_checksums:
                try:
                    logger.info(f"Adding new envelope for peer: {peer.web_ui_onion_url}")
                    peer_pubkey_obj = serialization.load_pem_public_key(peer.pubkey.encode())
                    encrypted_key = peer_pubkey_obj.encrypt(
                        original_aes_key,
                        rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                    )
                    manifest['encrypted_aes_keys'][peer_checksum] = base64.b64encode(encrypted_key).decode('utf-8')
                    updated = True
                except Exception as e:
                    logger.error(f"Failed to create new envelope for peer {peer.web_ui_onion_url}: {e}")
        
        if not updated:
            logger.info("No new peers found to add to the manifest.")
        
        return manifest

    def create_manifest_and_store_chunks(self, raw_data: bytes, recipients_pubkeys: Optional[List[str]] = None) -> dict:
        content_hash = hashlib.sha256(raw_data).hexdigest()
        aes_key = os.urandom(32)
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(raw_data) + padder.finalize()
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        chunks = [encrypted_data[i:i + CHUNK_SIZE] for i in range(0, len(encrypted_data), CHUNK_SIZE)]
        chunk_hashes = [hashlib.sha256(chunk).hexdigest() for chunk in chunks]
        content_chunk_dir = os.path.join(self.chunk_storage_path, content_hash)
        os.makedirs(content_chunk_dir, exist_ok=True)
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(content_chunk_dir, f"{i}.chunk")
            with open(chunk_path, 'wb') as f:
                f.write(chunk)
        
        encrypted_aes_keys = {}
        pubkeys_to_encrypt_for = set()

        # Always encrypt for the local instance (the sender)
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False, is_trusted_peer=False).first()
        if local_instance and local_instance.pubkey:
            pubkeys_to_encrypt_for.add(local_instance.pubkey)

        # Determine the set of recipients
        if recipients_pubkeys:
            # Private message: use the provided list of recipients' public keys
            for pkey in recipients_pubkeys:
                pubkeys_to_encrypt_for.add(pkey)
            logger.info(f"Creating private manifest for {len(pubkeys_to_encrypt_for)} recipient(s).")
        else:
            # Public content: encrypt for all trusted peers
            trusted_peers = TrustedInstance.objects.filter(is_trusted_peer=True)
            for peer in trusted_peers:
                if peer.pubkey:
                    pubkeys_to_encrypt_for.add(peer.pubkey)
            logger.info(f"Creating public manifest for {len(pubkeys_to_encrypt_for)} total instance(s).")

        # Create an encrypted "envelope" for each public key
        for pubkey_pem in pubkeys_to_encrypt_for:
            try:
                peer_pubkey_obj = serialization.load_pem_public_key(pubkey_pem.encode())
                encrypted_key = peer_pubkey_obj.encrypt(
                    aes_key,
                    rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                )
                instance_checksum = generate_checksum(pubkey_pem)
                encrypted_aes_keys[instance_checksum] = base64.b64encode(encrypted_key).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to encrypt AES key for pubkey with checksum {generate_checksum(pubkey_pem)}: {e}")
        
        manifest = {
            "content_hash": content_hash,
            "chunk_size": CHUNK_SIZE,
            "chunk_hashes": chunk_hashes,
            "encryption_iv": base64.b64encode(iv).decode('utf-8'),
            "encrypted_aes_keys": encrypted_aes_keys,
        }
        return manifest

    def get_chunk_path(self, content_hash: str, chunk_index: int) -> str:
        return os.path.join(self.chunk_storage_path, content_hash, f"{chunk_index}.chunk")
