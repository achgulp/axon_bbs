# axon_bbs/core/services/sync_service.py
import threading
import time
import requests
import logging
from django.utils import timezone
import json

from core.models import TrustedInstance, Message, MessageBoard

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()
        logger.info("Peer Sync Service started.")

    def _run(self):
        time.sleep(10)
        while True:
            try:
                self.poll_peers()
            except Exception as e:
                logger.error(f"Error in sync service poll loop: {e}", exc_info=True)
            time.sleep(self.poll_interval)

    def _process_magnet(self, magnet, peer_pubkey):
        # --- FIX: Moved the import here to break the circular dependency ---
        from .service_manager import service_manager
        
        try:
            logger.info(f"Processing magnet: {magnet[:40]}...")
            # Note: The download_and_decrypt arguments were incorrect, this is now fixed.
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
        peers = TrustedInstance.objects.filter(encrypted_private_key__isnull=True)
        if not peers.exists():
            return

        logger.info(f"Polling {peers.count()} trusted peer(s) for new messages...")
        for peer in peers:
            if not peer.web_ui_onion_url:
                continue

            last_sync = peer.last_synced_at or timezone.datetime.min.replace(tzinfo=timezone.utc)
            
            proxies = {}
            if '.onion' in peer.web_ui_onion_url:
                proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

            try:
                target_url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={last_sync.isoformat()}"
                
                with requests.Session() as session:
                    session.proxies = proxies
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
                    logger.warning(f"Failed to sync with peer {peer.web_ui_onion_url}: Status {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error while syncing with peer {peer.web_ui_onion_url}: {e}")
