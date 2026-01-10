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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


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
        is_runserver = 'runserver' in sys.argv
        is_reloader = os.environ.get('RUN_MAIN') == 'true'

        if is_runserver and is_reloader:
            from .models import TrustedInstance
            from django.conf import settings
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization

            local_instance, created = TrustedInstance.objects.get_or_create(is_trusted_peer=False)
            if created:
                logger.info("Created default local instance as it did not exist.")
            
            if not local_instance.encrypted_private_key:
                logger.warning("Local instance is missing private key. Generating new keys...")
                try:
                    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                    f = Fernet(key)
                    
                    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                    public_key_pem = private_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode('utf-8')
                    private_pem = private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ).decode('utf-8')
                    
                    encrypted_private = f.encrypt(private_pem.encode()).decode()
                    local_instance.pubkey = public_key_pem
                    local_instance.encrypted_private_key = encrypted_private
                    local_instance.save()
                    logger.info("Successfully generated and encrypted new keys for the local instance.")
                except Exception as e:
                    logger.error(f"FATAL: Could not generate keys for local instance: {e}")
            
            from django.contrib.sessions.models import Session
            try:
                Session.objects.all().delete()
                logger.info("All user sessions cleared on server startup.")
            except Exception as e:
                logger.error(f"Failed to clear sessions on startup: {e}")
            
            from .services.service_manager import service_manager
            
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

