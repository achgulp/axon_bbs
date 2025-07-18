# axon_bbs/core/services/service_manager.py
import logging
from django.conf import settings
from .tor_service import TorService
from .nostr_service import NostrService
import asyncio
import threading

logger = logging.getLogger(__name__)

class ServiceManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
            cls._instance.tor_service = None
            cls._instance.nostr_service = None
            cls._instance.loop = None
        return cls._instance

    def _run_async_services(self):
        """A target for our background thread to run the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Schedule the connection to run in the loop
        self.loop.create_task(self.nostr_service.connect())

        # Run the event loop forever
        self.loop.run_forever()

    def initialize_services(self):
        """
        Initializes all the core network services.
        """
        if not self.tor_service:
            print("--> Attempting to connect to Tor network...")
            tor_host = getattr(settings, "TOR_SOCKS_HOST", "127.0.0.1")
            tor_port = getattr(settings, "TOR_SOCKS_PORT", 9050)
            self.tor_service = TorService(host=tor_host, port=tor_port)
            if not self.tor_service.activate_proxy():
                 print("[!] CRITICAL: Failed to activate Tor proxy. Connections will NOT be anonymized.")
            else:
                print("--> Tor proxy activated successfully.")

        if not self.nostr_service:
            print("--> Initializing Nostr service...")
            # Now uses a list of relay URLs
            relay_urls = getattr(settings, "NOSTR_RELAY_URLS", ["wss://relay.damus.io"])
            self.nostr_service = NostrService(relay_urls=relay_urls, tor_service=self.tor_service)

            thread = threading.Thread(target=self._run_async_services, daemon=True)
            thread.start()
            print(f"--> Nostr connection thread started for relays: {', '.join(relay_urls)}.")

service_manager = ServiceManager()
