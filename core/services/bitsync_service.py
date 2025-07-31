# Full path: axon_bbs/core/services/bitsync_service.py
import os
import json
import hashlib
import logging
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from django.conf import settings
from django.db.models import Q
from core.models import TrustedInstance
from .encryption_utils import generate_checksum # UPDATED: Corrected the import path

logger = logging.getLogger(__name__)

# Define a constant for the chunk size (e.g., 256KB)
CHUNK_SIZE = 256 * 1024

class BitSyncService:
    """
    Handles the creation and storage of content for the BitSync P2P protocol.
    """
    def __init__(self):
        self.chunk_storage_path = os.path.join(settings.BASE_DIR, 'data', 'bitsync_chunks')
        os.makedirs(self.chunk_storage_path, exist_ok=True)
        logger.info("BitSyncService initialized. Chunk storage is at: %s", self.chunk_storage_path)

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

    def create_manifest_and_store_chunks(self, raw_data: bytes) -> dict:
        """
        Takes raw data, encrypts it, splits it into chunks, stores the chunks,
        and returns a complete manifest for distribution.
        :param raw_data: The raw bytes of the content to be shared.
        :return: A dictionary representing the content manifest.
        """
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
        logger.info(f"Stored {len(chunks)} chunks for content hash: {content_hash[:10]}...")
        encrypted_aes_keys = {}
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        trusted_peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        instances_to_encrypt_for = list(trusted_peers)
        if local_instance and local_instance not in instances_to_encrypt_for:
            instances_to_encrypt_for.append(local_instance)
        for instance in instances_to_encrypt_for:
            if instance.pubkey:
                try:
                    peer_pubkey_obj = serialization.load_pem_public_key(instance.pubkey.encode())
                    encrypted_key = peer_pubkey_obj.encrypt(
                        aes_key,
                        rsa_padding.OAEP(
                            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    instance_checksum = generate_checksum(instance.pubkey)
                    encrypted_aes_keys[instance_checksum] = base64.b64encode(encrypted_key).decode('utf-8')
                except Exception as e:
                    logger.error(f"Failed to encrypt AES key for instance {instance.web_ui_onion_url or 'local'}: {e}")
        manifest = {
            "content_hash": content_hash,
            "chunk_size": CHUNK_SIZE,
            "chunk_hashes": chunk_hashes,
            "encryption_iv": base64.b64encode(iv).decode('utf-8'),
            "encrypted_aes_keys": encrypted_aes_keys,
        }
        return manifest

    def get_chunk_path(self, content_hash: str, chunk_index: int) -> str:
        """
        Constructs the canonical file path for a requested chunk.
        This path is used for both saving and retrieving chunks.
        :param content_hash: The SHA256 hash of the content.
        :param chunk_index: The index of the chunk.
        :return: The absolute path to where the chunk file should be.
        """
        return os.path.join(self.chunk_storage_path, content_hash, f"{chunk_index}.chunk")
