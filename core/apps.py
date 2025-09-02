# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/apps.py
from django.apps import AppConfig
import logging
import os
import sys 
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
        # UPDATED: This logic is now corrected to ONLY start background services for the
        # main 'runserver' process. This prevents database queries from running during
        # commands like 'makemigrations' before the schema is up to date.
        is_runserver = 'runserver' in sys.argv
        is_reloader = os.environ.get('RUN_MAIN') == 'true'

        if is_runserver and is_reloader:
            from .services.service_manager import service_manager
            
            # This check prevents services from being initialized multiple times if ready()
            # is called more than once by the same process.
            if not service_manager.bitsync_service:
                logger.info("Starting background services for runserver...")
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

