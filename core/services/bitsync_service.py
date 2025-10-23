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
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#

# Full path: axon_bbs/core/services/bitsync_service.py
import os
import json
import hashlib
import logging
import base64
from typing import List, Optional, Union, Dict, Any

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
        logger.debug("BitSyncService initialized. Chunk storage is at: %s", self.chunk_storage_path)

    def are_all_chunks_local(self, manifest: dict) -> bool:
        if not manifest or 'chunk_hashes' not in manifest:
            return False

        content_hash = manifest.get('content_hash')
        num_chunks = len(manifest.get('chunk_hashes', []))

        for i in range(num_chunks):
            chunk_path = self.get_chunk_path(content_hash, i)
            if not os.path.exists(chunk_path):
                return False

        return True

    def get_manifest_cache_path(self, content_hash: str) -> str:
        """Returns the path where a manifest is cached alongside its chunks."""
        return os.path.join(self.chunk_storage_path, content_hash, '.manifest')

    def save_manifest_cache(self, manifest: dict):
        """Saves a manifest to disk alongside its chunks for rekey detection."""
        content_hash = manifest.get('content_hash')
        if not content_hash:
            return

        manifest_path = self.get_manifest_cache_path(content_hash)
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)

    def load_manifest_cache(self, content_hash: str) -> dict | None:
        """Loads a cached manifest from disk."""
        manifest_path = self.get_manifest_cache_path(content_hash)

        if not os.path.exists(manifest_path):
            return None

        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached manifest for {content_hash[:10]}: {e}")
            return None

    def detect_and_clear_rekeyed_chunks(self, new_manifest: dict) -> bool:
        """
        Detects if content has been rekeyed by comparing encryption IVs.
        If a rekey is detected, clears the old cached chunks.

        Returns True if chunks were cleared, False otherwise.
        """
        content_hash = new_manifest.get('content_hash')
        if not content_hash:
            logger.debug(f"detect_and_clear_rekeyed_chunks: No content_hash in manifest")
            return False

        # Load the cached manifest
        cached_manifest = self.load_manifest_cache(content_hash)
        if not cached_manifest:
            logger.debug(f"detect_and_clear_rekeyed_chunks: No cached manifest found for {content_hash[:10]}...")
            return False

        # Compare encryption IVs - different IV means content was rekeyed
        cached_iv = cached_manifest.get('encryption_iv')
        new_iv = new_manifest.get('encryption_iv')

        logger.debug(f"detect_and_clear_rekeyed_chunks for {content_hash[:10]}...: cached_iv={cached_iv[:20] if cached_iv else None}... new_iv={new_iv[:20] if new_iv else None}...")

        if cached_iv != new_iv:
            # Rekey detected! Clear the old chunks
            chunk_dir = os.path.join(self.chunk_storage_path, content_hash)
            if os.path.exists(chunk_dir):
                import shutil
                shutil.rmtree(chunk_dir)
                logger.info(f"Rekey detected for {content_hash[:10]}... (IV changed). Cleared stale cached chunks.")
                return True

        logger.debug(f"detect_and_clear_rekeyed_chunks: IVs match, no rekey detected for {content_hash[:10]}...")
        return False

    def _load_local_private_key(self):
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

    def rekey_manifest_for_peer(self, manifest: dict, peer_pubkey: str) -> dict:
        """
        Ensures a manifest has an encryption envelope for a specific peer.
        If the envelope already exists, it returns the manifest unchanged.
        If not, it decrypts the AES key and creates a new envelope for the peer.

        NOTE: This returns a NEW dict to avoid mutating the original manifest stored in the database.
        """
        peer_checksum = generate_checksum(peer_pubkey)
        if peer_checksum in manifest.get('encrypted_aes_keys', {}):
            return manifest # Already keyed for this peer, no work needed.

        logger.info(f"Performing on-demand rekey of manifest {manifest['content_hash'][:10]} for peer {peer_checksum[:10]}")

        original_aes_key = self.get_decrypted_aes_key(manifest)
        if not original_aes_key:
            raise ValueError("Failed to obtain original AES key from manifest for re-keying.")

        # Create a deep copy to avoid mutating the database object's manifest
        import copy
        rekeyed_manifest = copy.deepcopy(manifest)

        try:
            pubkey_obj = serialization.load_pem_public_key(peer_pubkey.encode())
            encrypted_key = pubkey_obj.encrypt(
                original_aes_key,
                rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            # Add the new key to the copied dictionary
            rekeyed_manifest['encrypted_aes_keys'][peer_checksum] = base64.b64encode(encrypted_key).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to create new envelope for peer with checksum {peer_checksum}: {e}")

        return rekeyed_manifest

    def rekey_manifest_for_new_peers(self, manifest: dict):
        original_aes_key = self.get_decrypted_aes_key(manifest)
        if not original_aes_key:
            raise ValueError("Failed to obtain original AES key from manifest.")

        all_instances = TrustedInstance.objects.filter(Q(is_trusted_peer=True) | Q(encrypted_private_key__isnull=False))
        
        new_encrypted_aes_keys = {}
        updated_count = 0

        for instance in all_instances:
            if not instance.pubkey:
                continue

            instance_checksum = generate_checksum(instance.pubkey)
            try:
                pubkey_obj = serialization.load_pem_public_key(instance.pubkey.encode())
                encrypted_key = pubkey_obj.encrypt(
                    original_aes_key,
                    rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                )
                new_encrypted_aes_keys[instance_checksum] = base64.b64encode(encrypted_key).decode('utf-8')
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to create new envelope for instance {instance.web_ui_onion_url or 'Local'}: {e}")
        
        manifest['encrypted_aes_keys'] = new_encrypted_aes_keys
        logger.info(f"Manifest re-keyed for {updated_count} total instance(s).")
        
        return manifest

    def create_encrypted_content(self, data: Dict[str, Any], recipients_pubkeys: Optional[List[str]] = None, b_b_s_instance_pubkeys: Optional[List[str]] = None) -> (str, Dict[str, Any]):
        raw_data = json.dumps(data, sort_keys=True).encode('utf-8')
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
            with open(os.path.join(content_chunk_dir, f"{i}.chunk"), 'wb') as f:
                f.write(chunk)
        
        encrypted_aes_keys = {}
        pubkeys_to_encrypt_for = set()

        if b_b_s_instance_pubkeys:
            for pkey in b_b_s_instance_pubkeys:
                pubkeys_to_encrypt_for.add(pkey)
        elif recipients_pubkeys:
            local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False, is_trusted_peer=False).first()
            if local_instance and local_instance.pubkey:
                pubkeys_to_encrypt_for.add(local_instance.pubkey)
            for pkey in recipients_pubkeys:
                pubkeys_to_encrypt_for.add(pkey)
        else:
            all_instances = TrustedInstance.objects.all()
            for instance in all_instances:
                if instance.pubkey:
                    pubkeys_to_encrypt_for.add(instance.pubkey)
        
        logger.info(f"Creating manifest for {len(pubkeys_to_encrypt_for)} total instance(s).")
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
        return content_hash, manifest

    def get_chunk_path(self, content_hash: str, chunk_index: int) -> str:
        return os.path.join(self.chunk_storage_path, content_hash, f"{chunk_index}.chunk")
