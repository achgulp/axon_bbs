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


# Full path: axon_bbs/core/services/tor_service.py
import os
import logging
import subprocess
import time
from django.conf import settings

logger = logging.getLogger(__name__)

class TorService:
    def __init__(self, host='127.0.0.1', port=9050):
        """Initialize Tor service with host and port for proxy."""
        self.host = host
        self.port = port
        self.process = None

    def start(self):
        """Start the Tor service."""
        try:
            # Assume Tor is installed and controlled via command line (adjust path if needed)
            self.process = subprocess.Popen(['tor', '-f', os.path.join(settings.BASE_DIR, 'torrc')], 
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(5)  # Wait for Tor to initialize
            logger.info(f"Tor service started on {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start Tor service: {e}")
            raise

    def stop(self):
        """Stop the Tor service."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            logger.info("Tor service stopped.")

    def get_proxy_port(self):
        """Return the proxy port."""
        return self.port

    def is_running(self):
        """Check if Tor is running."""
        return self.process and self.process.poll() is None
