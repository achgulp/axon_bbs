# Full path: axon_bbs/core/services/service_manager.py
import logging
from .bitsync_service import BitSyncService
from .tor_service import TorService
from .sync_service import SyncService # NEW: Import SyncService

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        """
        Initializes and manages the core background services for the application.
        """
        self.tor_service = TorService(host='127.0.0.1', port=9050)
        self.bitsync_service = None
        self.sync_service = None # NEW: Add placeholder for SyncService

    def initialize_services(self):
        """
        Initializes all necessary services in the correct order.
        """
        logger.info("Initializing Tor service...")
        # self.tor_service.start() # Assuming Tor is managed externally for now

        logger.info("Initializing BitSync service...")
        self.bitsync_service = BitSyncService()
        
        # NEW: Instantiate and start the SyncService from here
        logger.info("Initializing and starting SyncService thread...")
        self.sync_service = SyncService()
        self.sync_service.start()
        
        logger.info("All services initialized.")

    def shutdown(self):
        """
        Gracefully shuts down all managed services.
        """
        if self.tor_service and self.tor_service.is_running():
            logger.info("Shutting down Tor service...")
            self.tor_service.stop()

# Create a single, globally accessible instance of the ServiceManager.
service_manager = ServiceManager()

