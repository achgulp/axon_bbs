# Full path: axon_bbs/core/apps.py
from django.apps import AppConfig
import logging
import os
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        This method is called by Django when the application is ready.
        It initializes all global services via the ServiceManager.
        """
        # The RUN_MAIN check ensures this only runs once in the main Django process.
        if os.environ.get('RUN_MAIN') == 'true':
            from .services.service_manager import service_manager
            
            # The ServiceManager now handles the initialization and start
            # of all background services, including the SyncService.
            service_manager.initialize_services()

@receiver(post_migrate)
def clear_sessions_after_migrate(sender, **kwargs):
    """Clears all active sessions after migrations (post-startup)."""
    from django.contrib.sessions.models import Session
    try:
        Session.objects.all().delete()
        logger.info("All user sessions cleared after startup/migrations.")
    except Exception as e:
        logger.error(f"Failed to clear sessions: {e}")

