# Full path: axon_bbs/core/apps.py
from django.apps import AppConfig
import logging
import os
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .services.encryption_utils import generate_checksum

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

            # Log trusted peers count and checksums on boot
            from .models import TrustedInstance
            peers = TrustedInstance.objects.filter(is_trusted_peer=True)
            num_peers = peers.count()
            logger.info(f"Number of trusted peers: {num_peers}")
            if num_peers > 0:
                logger.info("Trusted peer checksums (one per line):")
                for peer in peers:
                    if peer.pubkey:
                        checksum = generate_checksum(peer.pubkey)
                        logger.info(f"{checksum} ({peer.web_ui_onion_url or 'No URL'})")
                    else:
                        logger.info("No pubkey for peer")

            # Handle first-time start (e.g., setup flag)
            flag_path = os.path.join(settings.BASE_DIR, 'data', 'first_start.flag')
            if not os.path.exists(flag_path):
                logger.info("First-time start detected. Performing initial setup...")
                # Add any first-start logic here (e.g., create default board)
                with open(flag_path, 'w') as f:
                    f.write('started')

@receiver(post_migrate)
def clear_sessions_after_migrate(sender, **kwargs):
    """Clears all active sessions after migrations (post-startup)."""
    from django.contrib.sessions.models import Session
    try:
        Session.objects.all().delete()
        logger.info("All sessions cleared after startup/migrations.")
    except Exception as e:
        logger.error(f"Failed to clear sessions: {e}")
