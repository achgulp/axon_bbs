# Full path: axon_bbs/core/services/sync_service.py
import threading
import time
import requests
import logging
from django.utils import timezone
import json
import datetime
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1

from core.models import TrustedInstance, Message, MessageBoard
from .encryption_utils import generate_checksum

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()
        logger.info("Peer Sync Service started.")

    def _run(self):
        time.sleep(15)
        while True:
            try:
                self.poll_peers()
            except Exception as e:
                logger.error(f"Error in sync service poll loop: {e}", exc_info=True)
            time.sleep(self.poll_interval)

    def _process_magnet(self, magnet, peer_pubkey):
        from core.services.service_manager import service_manager
        
        try:
            logger.info(f"Processing magnet: {magnet[:40]}...")
            handle, decrypted_content = service_manager.bittorrent_service.download_and_decrypt(
                magnet, 'data/sync', peer_pubkey
            )
            
            if decrypted_content:
                content = json.loads(decrypted_content.decode())
                board_name = content.get('board', 'general')
                board, _ = MessageBoard.objects.get_or_create(name=board_name)
                
                if not Message.objects.filter(subject=content.get('subject'), pubkey=content.get('pubkey')).exists():
                    Message.objects.create(
                        board=board,
                        subject=content.get('subject'),
                        body=content.get('body'),
                        pubkey=content.get('pubkey')
                    )
                    logger.info(f"Successfully synced new message: {content.get('subject')}")
                else:
                    logger.info("Message already exists, skipping.")
        except Exception as e:
            logger.error(f"Failed to process magnet {magnet[:40]}: {e}", exc_info=True)


    def poll_peers(self):
        from core.services.service_manager import service_manager
        
        peers = TrustedInstance.objects.filter(encrypted_private_key__exact='')
        if not peers.exists():
            logger.info("Sync service found no peers to poll.")
            return

        logger.info(f"Polling {peers.count()} trusted peer(s) for new messages...")
        
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        if not local_instance:
            logger.warning("Cannot poll peers: local instance identity not found.")
            return
        
        private_key = service_manager.bittorrent_service.get_private_key()
        if not private_key:
            logger.warning("Cannot poll peers: local private key not loaded.")
            return
            
        local_pubkey = local_instance.pubkey
        
        # --- FINAL DEBUG LOGGING ---
        local_key_checksum = generate_checksum(local_pubkey)
        logger.info(f"SYNC-OUT: Loaded local key for signing. Checksum: {local_key_checksum}")
        # Log full local pubkey for debugging (sanitized)
        logger.debug(f"Local pubkey (length: {len(local_pubkey)}): {local_pubkey[:50]}...{local_pubkey[-50:]}")
        # --- END DEBUG LOGGING ---

        for peer in peers:
            if not peer.web_ui_onion_url:
                continue

            last_sync = peer.last_synced_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            
            proxies = {}
            if '.onion' in peer.web_ui_onion_url:
                proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

            try:
                timestamp = timezone.now().isoformat()
                hasher = hashes.Hash(hashes.SHA256())
                hasher.update(timestamp.encode())
                digest = hasher.finalize()
                
                signature = private_key.sign(
                    digest, PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH), hashes.SHA256()
                )
                signature_b64 = base64.b64encode(signature).decode('utf-8')

                # Base64 encode the pubkey to avoid newline issues in headers
                header_pubkey_b64 = base64.b64encode(local_pubkey.encode()).decode('utf-8')
                logger.debug(f"Encoded pubkey_b64 for header (length: {len(header_pubkey_b64)}): {header_pubkey_b64[:50]}...{header_pubkey_b64[-50:]}")

                headers = {
                    'X-Pubkey': header_pubkey_b64,
                    'X-Timestamp': timestamp,
                    'X-Signature': signature_b64
                }

                target_url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={last_sync.isoformat()}"
                
                with requests.Session() as session:
                    session.proxies = proxies
                    session.headers.update(headers)
                    response = session.get(target_url, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    new_magnets = data.get('magnets', [])
                    if new_magnets:
                        logger.info(f"Received {len(new_magnets)} new magnet(s) from peer {peer.web_ui_onion_url}")
                        for magnet in new_magnets:
                            self._process_magnet(magnet, peer.pubkey)

                    peer.last_synced_at = timezone.now()
                    peer.save()
                else:
                    logger.warning(f"Failed to sync with peer {peer.web_ui_onion_url}: Status {response.status_code} Body: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error while syncing with peer {peer.web_ui_onion_url}: {e}")
