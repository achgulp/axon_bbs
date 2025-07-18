# axon_bbs/core/apps.py
from django.apps import AppConfig
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        This method is called by Django when the application is ready.
        It's the perfect place to initialize our global services and clear sessions on startup.
        """
        if os.environ.get('RUN_MAIN') == 'true':  # Only run in the child process
            logger.info("Core app is ready. Initializing global services...")
            from .services.service_manager import service_manager
            
            # Initialize all services defined in the ServiceManager
            service_manager.initialize_services()

            # Clear all sessions on startup/restart
            self.clear_sessions()

            # Handle first-time start (e.g., setup flag)
            flag_path = os.path.join(settings.BASE_DIR, 'data', 'first_start.flag')
            if not os.path.exists(flag_path):
                logger.info("First-time start detected. Performing initial setup...")
                # Add any first-start logic here (e.g., create default board)
                with open(flag_path, 'w') as f:
                    f.write('started')

    def clear_sessions(self):
        """Clears all active sessions from the database on startup."""
        from django.contrib.sessions.models import Session  # Lazy import to avoid AppRegistryNotReady
        try:
            Session.objects.all().delete()
            logger.info("All sessions cleared on startup.")
        except Exception as e:
            logger.error(f"Failed to clear sessions: {e}")
