# Full path: axon_bbs/core/services/service_manager.py
import logging
from .bitsync_service import BitSyncService # UPDATED: Import BitSyncService
from .tor_service import TorService

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        """
        Initializes and manages the core background services for the application.
        """
        self.tor_service = TorService(host='127.0.0.1', port=9050)
        self.bitsync_service = None # UPDATED: Changed from bittorrent_service

    def initialize_services(self):
        """
        Initializes all necessary services in the correct order.
        The Tor service must be started before services that depend on it.
        """
        logger.info("Initializing Tor service...")
        # In a real deployment, you might have more robust start/check logic.
        # For now, we assume it starts or is already running.
        # self.tor_service.start() 

        logger.info("Initializing BitSync service...")
        self.bitsync_service = BitSyncService() # UPDATED: Instantiate BitSyncService
        
        logger.info("All services initialized.")

    def shutdown(self):
        """
        Gracefully shuts down all managed services.
        """
        # The new BitSyncService doesn't have a persistent connection or thread
        # that needs explicit shutdown, so we only need to handle the Tor service.
        if self.tor_service and self.tor_service.is_running():
            logger.info("Shutting down Tor service...")
            self.tor_service.stop()

# Create a single, globally accessible instance of the ServiceManager.
# This singleton pattern ensures all parts of the Django app use the same
# service instances.
service_manager = ServiceManager()

