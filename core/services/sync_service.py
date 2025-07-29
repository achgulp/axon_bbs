# Full path: axon_bbs/core/services/sync_service.py
import threading
import time
import requests
import logging
import json
import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from django.utils import timezone as django_timezone
from django.conf import settings
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from core.models import TrustedInstance, Message, MessageBoard
from .encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, poll_interval=120): # UPDATED: Poll every 2 minutes
        self.poll_interval = poll_interval
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.local_instance = None
        self.private_key = None

    def start(self):
        self.thread.start()
        logger.info("BitSync Service thread started. Polling will begin shortly.")

    def _run(self):
        time.sleep(15) 
        logger.info("SyncService polling loop is now active.")
        while True:
            try:
                self._load_identity()
                if self.local_instance and self.private_key:
                    self.poll_peers()
                else:
                    logger.warning("Sync service cannot run without a configured local instance identity. Will check again in %s seconds.", self.poll_interval)
            except Exception as e:
                logger.error(f"Error in sync service poll loop: {e}", exc_info=True)
            time.sleep(self.poll_interval)
    
    def _load_identity(self):
        """Loads the local instance and decrypts its private key."""
        try:
            self.local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
            if self.local_instance and self.local_instance.encrypted_private_key:
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                from cryptography.fernet import Fernet
                f = Fernet(key)
                decrypted_pem = f.decrypt(self.local_instance.encrypted_private_key.encode())
                self.private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
        except Exception as e:
            logger.error(f"Failed to load local identity for sync service: {e}")
            self.local_instance = None
            self.private_key = None

    def _get_auth_headers(self):
        """Generates the necessary authentication headers for an API request."""
        timestamp = datetime.now(timezone.utc).isoformat()
        hasher = hashlib.sha256()
        hasher.update(timestamp.encode('utf-8'))
        digest = hasher.digest()
        
        signature = self.private_key.sign(
            digest,
            rsa_padding.PSS(
                mgf=rsa_padding.MGF1(hashes.SHA256()),
                salt_length=rsa_padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return {
            'X-Pubkey': base64.b64encode(self.local_instance.pubkey.encode('utf-8')).decode('utf-8'),
            'X-Timestamp': timestamp,
            'X-Signature': base64.b64encode(signature).decode('utf-8')
        }

    def poll_peers(self):
        """Polls all trusted peers for new content manifests."""
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        
        if not peers.exists():
            logger.info("Polling complete. No trusted peers are configured to sync with.")
            return

        logger.info(f"Beginning poll of {peers.count()} trusted peer(s)...")
        for peer in peers:
            if not peer.web_ui_onion_url:
                logger.warning(f"Skipping peer ID {peer.id} because it has no .onion URL set.")
                continue

            logger.info(f"--> Checking peer: {peer.web_ui_onion_url}")
            last_sync = peer.last_synced_at or datetime.min.replace(tzinfo=timezone.utc)
            proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
            
            try:
                target_url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={last_sync.isoformat()}"
                response = requests.get(target_url, headers=self._get_auth_headers(), proxies=proxies, timeout=120)

                if response.status_code == 200:
                    manifests = response.json().get('manifests', [])
                    logger.info(f"<-- Received {len(manifests)} new manifest(s) from peer {peer.web_ui_onion_url}")
                    for manifest in manifests:
                        self._process_manifest(manifest)
                    peer.last_synced_at = django_timezone.now()
                    peer.save()
                else:
                    logger.warning(f"<-- Failed to sync with peer {peer.web_ui_onion_url}: Status {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"<-- Network error while contacting peer {peer.web_ui_onion_url}: {e}")
        
        logger.info("Polling cycle complete.")

    def _process_manifest(self, manifest: dict):
        """Processes a single manifest, discovering seeders and initiating the download."""
        content_hash = manifest.get('content_hash')
        if not content_hash:
            logger.warning("Received a manifest with no content_hash, skipping.")
            return

        if Message.objects.filter(manifest__content_hash=content_hash).exists():
            logger.info(f"Content {content_hash[:10]}... already exists, skipping download.")
            return

        logger.info(f"Processing new content {content_hash[:10]}...")
        seeders = self._find_seeders(content_hash)
        if not seeders:
            logger.warning(f"No seeders found for content {content_hash[:10]}... Will retry on next poll.")
            return
        
        self._download_content(manifest, seeders)

    def _find_seeders(self, content_hash: str) -> list:
        """Queries all trusted peers to see who has the specified content."""
        logger.info(f"Discovering seeders for content {content_hash[:10]}...")
        available_seeders = []
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

        for peer in peers:
            if not peer.web_ui_onion_url:
                continue
            try:
                url = f"{peer.web_ui_onion_url.strip('/')}/api/bitsync/has_content/{content_hash}/"
                response = requests.get(url, headers=self._get_auth_headers(), proxies=proxies, timeout=60)
                if response.status_code == 200:
                    available_seeders.append(peer.web_ui_onion_url)
                    logger.info(f"Peer {peer.web_ui_onion_url} has content {content_hash[:10]}...")
            except requests.RequestException:
                logger.warning(f"Could not contact peer {peer.web_ui_onion_url} to check for content.")
        
        return available_seeders

    def _download_content(self, manifest: dict, seeders: list):
        """Orchestrates the parallel download of chunks from a list of available seeders."""
        content_hash = manifest['content_hash']
        chunk_hashes = manifest['chunk_hashes']
        num_chunks = len(chunk_hashes)
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        
        downloaded_chunks = {}
        
        logger.info(f"Starting swarm download for {content_hash[:10]}... from {len(seeders)} peer(s).")

        with ThreadPoolExecutor(max_workers=len(seeders) * 2) as executor:
            futures = {
                executor.submit(self._download_chunk, seeder_url, content_hash, i, proxies): i
                for i, seeder_url in enumerate(seeders * (num_chunks // len(seeders) + 1))
                if i < num_chunks
            }
            
            for future in as_completed(futures):
                chunk_index, chunk_data = future.result()
                if chunk_data and hashlib.sha256(chunk_data).hexdigest() == chunk_hashes[chunk_index]:
                    downloaded_chunks[chunk_index] = chunk_data
                    logger.info(f"Successfully downloaded and verified chunk {chunk_index + 1}/{num_chunks} for {content_hash[:10]}...")
                else:
                    logger.error(f"Failed to download or verify chunk {chunk_index} for {content_hash[:10]}...")
        
        if len(downloaded_chunks) == num_chunks:
            logger.info(f"All {num_chunks} chunks for {content_hash[:10]}... downloaded. Reassembling...")
            encrypted_data = b"".join(downloaded_chunks[i] for i in range(num_chunks))
            self._decrypt_and_save(encrypted_data, manifest)
        else:
            logger.error(f"Failed to download all chunks for {content_hash[:10]}... Downloaded {len(downloaded_chunks)}/{num_chunks}.")

    def _download_chunk(self, seeder_url, content_hash, chunk_index, proxies):
        """Downloads a single chunk from a given seeder."""
        try:
            url = f"{seeder_url.strip('/')}/api/bitsync/chunk/{content_hash}/{chunk_index}/"
            response = requests.get(url, headers=self._get_auth_headers(), proxies=proxies, timeout=120)
            if response.status_code == 200:
                return chunk_index, response.content
        except requests.RequestException as e:
            logger.warning(f"Failed to download chunk {chunk_index} from {seeder_url}: {e}")
        return chunk_index, None

    def _decrypt_and_save(self, encrypted_data: bytes, manifest: dict):
        """Decrypts the reassembled data and saves it as a new Message."""
        try:
            local_checksum = generate_checksum(self.local_instance.pubkey)
            encrypted_aes_key_b64 = manifest['encrypted_aes_keys'].get(local_checksum)
            if not encrypted_aes_key_b64:
                logger.error("Could not find an encryption envelope for our key in the manifest.")
                return

            encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
            aes_key = self.private_key.decrypt(
                encrypted_aes_key,
                rsa_padding.OAEP(
                    mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            iv = base64.b64decode(manifest['encryption_iv'])
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
            unpadder = PKCS7(algorithms.AES.block_size).unpadder()
            padded_data = cipher.decryptor().update(encrypted_data)
            raw_data = unpadder.update(padded_data) + unpadder.finalize()
            
            content = json.loads(raw_data.decode('utf-8'))
            
            board, _ = MessageBoard.objects.get_or_create(name=content.get('board', 'general'))
            Message.objects.create(
                board=board,
                subject=content.get('subject'),
                body=content.get('body'),
                pubkey=content.get('pubkey'),
                manifest=manifest
            )
            logger.info(f"Successfully synced and saved new message: '{content.get('subject')}'")

        except Exception as e:
            logger.error(f"Failed to decrypt or save content {manifest['content_hash'][:10]}...: {e}", exc_info=True)

