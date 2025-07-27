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
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SyncService, cls).__new__(cls)
        return cls._instance

    def __init__(self, poll_interval=60):
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        self.poll_interval = poll_interval
        self.thread = None
        self.stop_event = threading.Event()
        self._initialized = True

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("Peer Sync Service started.")

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join()
        logger.info("Peer Sync Service stopped.")

    def _run(self):
        logger.info("SyncService polling thread is running.")
        time.sleep(15)  # Initial delay before first poll
        while not self.stop_event.is_set():
            try:
                self.poll_peers()
            except Exception as e:
                logger.error(f"Error in sync service poll loop: {e}", exc_info=True)
            self.stop_event.wait(self.poll_interval)
        logger.info("SyncService polling thread has exited.")


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
                
                # Check for duplicates before creating
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
        
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        if not peers.exists():
            # This is normal, so we can lower the log level
            logger.debug("Sync service found no peers to poll.")
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
                header_pubkey_b64 = base64.b64encode(local_pubkey.encode()).decode('utf-8')
   
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
