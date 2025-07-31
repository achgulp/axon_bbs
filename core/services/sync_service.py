# Full path: axon_bbs/core/services/sync_service.py
import threading
import time
import requests
import logging
import json
import base64
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from django.utils import timezone as django_timezone
from django.conf import settings
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from core.models import TrustedInstance, Message, MessageBoard, FileAttachment
from .encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, poll_interval=120):
        self.poll_interval = poll_interval
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.local_instance = None
        self.private_key = None
        max_file_downloads = getattr(settings, 'BITSYNC_MAX_CONCURRENT_FILES', 3)
        self.download_executor = ThreadPoolExecutor(max_workers=max_file_downloads, thread_name_prefix='download_worker')
        self.currently_downloading = set()

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
            self.local_instance, self.private_key = None, None

    
    def _get_auth_headers(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        hasher = hashlib.sha256(timestamp.encode('utf-8'))
        digest = hasher.digest()
        signature = self.private_key.sign(
            digest, rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH), hashes.SHA256()
        )
        return {
            'X-Pubkey': base64.b64encode(self.local_instance.pubkey.encode('utf-8')).decode('utf-8'),
            'X-Timestamp': timestamp,
            'X-Signature': base64.b64encode(signature).decode('utf-8')
        }

    def poll_peers(self):
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        if not peers.exists():
            logger.info("Polling complete. No trusted peers are configured to sync with.")
            return
        
        logger.info(f"Beginning poll of {peers.count()} trusted peer(s)...")
        for peer in peers:
            logger.info(f"--> Checking peer: {peer.web_ui_onion_url}")
            last_sync = peer.last_synced_at or datetime.min.replace(tzinfo=timezone.utc)
            proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
            
            # UPDATED: Re-structured with a finally block for guaranteed timestamp updates
            server_timestamp_str = None
            try:
                target_url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={last_sync.isoformat()}"
                response = requests.get(target_url, headers=self._get_auth_headers(), proxies=proxies, timeout=120)
                
                if response.status_code == 200:
                    response_data = response.json()
                    manifests = response_data.get('manifests', [])
                    server_timestamp_str = response_data.get('server_timestamp')
                    logger.info(f"<-- Received {len(manifests)} new manifest(s) from peer {peer.web_ui_onion_url}")
                    if manifests:
                        self._process_manifests_in_order(manifests)
                else:
                    logger.warning(f"<-- Failed to sync with peer {peer.web_ui_onion_url}: Status {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                logger.error(f"<-- Network error while contacting peer {peer.web_ui_onion_url}: {e}")

            finally:
                # This block runs regardless of success or failure, preventing stale timestamps.
                if server_timestamp_str:
                    peer.last_synced_at = django_timezone.datetime.fromisoformat(server_timestamp_str)
                else:
                    # If the request failed or the peer is old, we must still advance our clock to avoid getting stuck.
                    peer.last_synced_at = django_timezone.now()
                peer.save()
                logger.info(f"Timestamp for peer {peer.web_ui_onion_url} updated to {peer.last_synced_at.isoformat()}")

        logger.info("Polling cycle complete.")

    def _schedule_download(self, manifest):
        """Submits a download task to the executor pool if not already running."""
        content_hash = manifest.get('content_hash')
        if content_hash in self.currently_downloading:
            logger.debug(f"Download for {content_hash[:10]}... is already in progress. Skipping.")
            return
        
        item_name = manifest.get('filename', content_hash[:16])
        logger.info(f"Scheduling download for: '{item_name}'")
        self.currently_downloading.add(content_hash)
        
        future = self.download_executor.submit(self._download_content, manifest)
        future.add_done_callback(lambda f: self.currently_downloading.discard(content_hash))

    def _process_manifests_in_order(self, manifests: list):
        all_content_items = []
        for manifest in manifests:
            content_hash = manifest['content_hash']
            content_type = manifest.get('content_type')
            
            if content_type == 'file':
                item, _ = FileAttachment.objects.get_or_create(
                    manifest__content_hash=content_hash, defaults={'manifest': manifest, 'filename': manifest.get('filename', 'unknown')}
                )
                all_content_items.append(item)
            elif content_type == 'message':
                try:
                    item = Message.objects.get(manifest__content_hash=content_hash)
                    all_content_items.append(item)
                except Message.DoesNotExist:
                    self._schedule_download(manifest)

        from .service_manager import service_manager
        for item in all_content_items:
            if not service_manager.bitsync_service.are_all_chunks_local(item.manifest):
                self._schedule_download(item.manifest)
        
    def _find_seeders(self, content_hash: str) -> list:
        logger.info(f"Discovering seeders for content {content_hash[:10]}...")
        available_seeders = []
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        for peer in peers:
            if not peer.web_ui_onion_url: continue
            try:
                url = f"{peer.web_ui_onion_url.strip('/')}/api/bitsync/has_content/{content_hash}/"
                response = requests.get(url, headers=self._get_auth_headers(), proxies=proxies, timeout=60)
                if response.status_code == 200:
                    available_seeders.append(peer.web_ui_onion_url)
                    logger.info(f"Peer {peer.web_ui_onion_url} has content {content_hash[:10]}...")
            except requests.RequestException:
                logger.warning(f"Could not contact peer {peer.web_ui_onion_url} to check for content.")
        return available_seeders

    def _download_content(self, manifest: dict) -> bytes | None:
        content_hash, chunk_hashes = manifest['content_hash'], manifest['chunk_hashes']
        num_chunks = len(chunk_hashes)
        item_name = manifest.get('filename', content_hash[:16])
        
        from .service_manager import service_manager
        
        if service_manager.bitsync_service.are_all_chunks_local(manifest):
            logger.info(f"All chunks for '{item_name}' already present locally.")
            self._create_message_from_manifest_if_needed(manifest)
            local_chunks_data = b""
            for i in range(num_chunks):
                chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, i)
                with open(chunk_path, 'rb') as f:
                    local_chunks_data += f.read()
            return local_chunks_data

        seeders = self._find_seeders(content_hash)
        if not seeders:
            logger.error(f"Cannot download '{item_name}': No seeders found.")
            return None
        
        logger.info(f"Starting swarm download for '{item_name}' from {len(seeders)} peer(s).")
        downloaded_chunks = {}
        for i in range(num_chunks):
            chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, i)
            if chunk_path and os.path.exists(chunk_path):
                 with open(chunk_path, 'rb') as f:
                    downloaded_chunks[i] = f.read()

        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        chunks_to_download = [i for i in range(num_chunks) if i not in downloaded_chunks]
        
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix='chunk_worker') as executor:
            futures = {
                executor.submit(self._download_chunk, seeders[i % len(seeders)], content_hash, chunk_idx, proxies): chunk_idx
                for i, chunk_idx in enumerate(chunks_to_download)
            }
            for future in as_completed(futures):
                chunk_index, chunk_data = future.result()
                if chunk_data and hashlib.sha256(chunk_data).hexdigest() == chunk_hashes[chunk_index]:
                    downloaded_chunks[chunk_index] = chunk_data
                    chunk_save_path = service_manager.bitsync_service.get_chunk_path(content_hash, chunk_index)
                    if chunk_save_path:
                         os.makedirs(os.path.dirname(chunk_save_path), exist_ok=True)
                         with open(chunk_save_path, 'wb') as f:
                             f.write(chunk_data)
                    logger.info(f"  - Chunk {chunk_index + 1}/{num_chunks} for '{item_name}' downloaded.")
                else: 
                    logger.error(f"  - Failed to download/verify chunk {chunk_index + 1} for '{item_name}'. Will retry on next sync.")

        if len(downloaded_chunks) == num_chunks:
            logger.info(f"Download complete for '{item_name}'.")
            self._create_message_from_manifest_if_needed(manifest)
            return b"".join(downloaded_chunks[i] for i in range(num_chunks))
        else:
            logger.error(f"Download for '{item_name}' is incomplete. Will retry on next sync cycle.")
            return None

    def _download_chunk(self, seeder_url, content_hash, chunk_index, proxies):
        try:
            url = f"{seeder_url.strip('/')}/api/bitsync/chunk/{content_hash}/{chunk_index}/"
            response = requests.get(url, headers=self._get_auth_headers(), proxies=proxies, timeout=120)
            if response.status_code == 200: return chunk_index, response.content
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download chunk {chunk_index} from {seeder_url}: {e}")
        return chunk_index, None

    def _decrypt_data(self, encrypted_data: bytes, manifest: dict) -> bytes | None:
        if not encrypted_data: return None
        try:
            local_checksum = generate_checksum(self.local_instance.pubkey)
            encrypted_aes_key_b64 = manifest['encrypted_aes_keys'].get(local_checksum)
            if not encrypted_aes_key_b64:
                logger.error("Could not find an encryption envelope for our key in the manifest.")
                return None
            encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
            aes_key = self.private_key.decrypt(
                encrypted_aes_key,
                rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            iv = base64.b64decode(manifest['encryption_iv'])
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
            unpadder = PKCS7(algorithms.AES.block_size).unpadder()
            padded_data = cipher.decryptor().update(encrypted_data)
            return unpadder.update(padded_data) + unpadder.finalize()
        except Exception as e:
            logger.error(f"Failed to decrypt content {manifest['content_hash'][:10]}...: {e}", exc_info=True)
            return None

    def get_decrypted_content(self, manifest: dict) -> bytes | None:
        content_hash = manifest.get('content_hash')
        if content_hash in self.currently_downloading:
            logger.info("Content is being downloaded by the background service; UI download will wait.")

        encrypted_data = self._download_content(manifest)
        if encrypted_data:
            return self._decrypt_data(encrypted_data, manifest)
        return None

    def _create_message_from_manifest_if_needed(self, manifest: dict):
        """After content is downloaded, this creates the DB entry if it's a message."""
        content_hash = manifest.get('content_hash')
        if manifest.get('content_type') != 'message' or Message.objects.filter(manifest__content_hash=content_hash).exists():
            return
        
        logger.info(f"Processing newly completed message content for hash {content_hash[:10]}...")
        encrypted_data = self._download_content(manifest)
        if not encrypted_data: return
        decrypted_data = self._decrypt_data(encrypted_data, manifest)
        if not decrypted_data: return
        
        try:
            content = json.loads(decrypted_data)
            board, _ = MessageBoard.objects.get_or_create(name=content.get('board', 'general'))
            message = Message.objects.create(
                board=board, subject=content.get('subject'), body=content.get('body'),
                pubkey=content.get('pubkey'), manifest=manifest
            )
            if 'attachment_hashes' in content:
                attachments = FileAttachment.objects.filter(manifest__content_hash__in=content['attachment_hashes'])
                if attachments.exists():
                    message.attachments.set(attachments)
                    logger.info(f"Successfully linked {attachments.count()} attachment(s) to message '{content.get('subject')}'.")
            logger.info(f"Successfully saved new message: '{content.get('subject')}'")
        except Exception as e:
            logger.error(f"Failed to create message from manifest {content_hash[:10]}: {e}")
