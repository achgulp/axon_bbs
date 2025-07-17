# axon_bbs/core/apps.py
from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        This method is called by Django when the application is ready.
        It's the perfect place to initialize our global services.
        """
        if os.environ.get('RUN_MAIN') == 'true':  # Only run in the child process
            logger.info("Core app is ready. Initializing global services...")
            from .services.service_manager import service_manager
            
            # Initialize all services defined in the ServiceManager
            service_manager.initialize_services()
