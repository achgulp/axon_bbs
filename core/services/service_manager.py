# axon_bbs/core/services/service_manager.py
import logging
from django.conf import settings
from .tor_service import TorService
from .bittorrent_service import BitTorrentService
from .sync_service import SyncService
import asyncio
import threading

logger = logging.getLogger(__name__)

class ServiceManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
            cls._instance.tor_service = None
            cls._instance.bittorrent_service = None
            cls._instance.sync_service = None
            cls._instance.loop = None
        return cls._instance

    def _run_async_services(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.bittorrent_service.start_session())
        self.loop.run_forever()

    def initialize_services(self):
        if not self.tor_service:
            print("--> Connecting to Tor...")
            tor_host = getattr(settings, "TOR_SOCKS_HOST", "127.0.0.1")
            tor_port = getattr(settings, "TOR_SOCKS_PORT", 9050)
            self.tor_service = TorService(host=tor_host, port=tor_port)
            if not self.tor_service.activate_proxy():
                print("[!] Failed to activate Tor proxy.")
            else:
                print("--> Tor proxy active.")

        if not self.bittorrent_service:
            print("--> Initializing BitTorrent service...")
            self.bittorrent_service = BitTorrentService(tor_service=self.tor_service)
            
            # --- FIX: Explicitly load/generate the key on startup ---
            self.bittorrent_service.prime_identity()
            
            thread = threading.Thread(target=self._run_async_services, daemon=True)
            thread.start()
            print("--> BitTorrent thread started.")

        if not self.sync_service:
            print("--> Initializing Peer Sync service...")
            self.sync_service = SyncService()
            self.sync_service.start()
            print("--> Peer Sync thread started.")

service_manager = ServiceManager()
