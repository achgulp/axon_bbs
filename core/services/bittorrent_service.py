# Full path: axon_bbs/core/services/bittorrent_service.py
import asyncio
import base64
import json
import logging
import os
import tempfile
import time
import re
import traceback # Import traceback for debugging
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.fernet import Fernet
from django.conf import settings
import libtorrent as lt

from core.models import TrustedInstance

logger = logging.getLogger(__name__)

def sanitize_filename(name):
    """Removes invalid characters for a filename."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

class BitTorrentService:
    def __init__(self, tor_service=None):
        self.tor_service = tor_service
        self.session = None
        self.identity_primed = False
        self.private_key = None
        self.torrent_save_path = os.path.join(settings.BASE_DIR, 'data', 'torrents')
        os.makedirs(self.torrent_save_path, exist_ok=True)


    async def start_session(self):
        settings_pack = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'proxy_hostname': '127.0.0.1',
            'proxy_port': 9050,
            'proxy_type': lt.proxy_type_t.socks5,
            'anonymous_mode': True
        }
        self.session = lt.session(settings_pack)
        self.session.add_dht_router('router.bittorrent.com', 6881)
        logger.info("BitTorrent session started with Tor proxy.")

    def prime_identity(self):
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        if not local_instance:
            logger.warning("No local instance identity found. Skipping priming.")
            return
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        try:
            self.private_key = serialization.load_pem_private_key(
                f.decrypt(local_instance.encrypted_private_key.encode()),
                password=None
            )
            self.identity_primed = True
            logger.info("Local identity primed successfully.")
        except Exception as e:
            logger.error(f"Failed to prime local identity: {e}", exc_info=True)

    def get_private_key(self):
        if not self.identity_primed:
            self.prime_identity()
        return self.private_key

    def create_torrent(self, data, name):
        sanitized_name = sanitize_filename(name)
        blob_filename = f"{sanitized_name}_{int(time.time())}.dat"
        blob_filepath = os.path.join(self.torrent_save_path, blob_filename)
        
        logger.debug(f"Creating torrent for '{name}' with sanitized filename '{blob_filename}'")

        enc_data, metadata = self.encrypt_and_wrap(data)
        try:
            with open(blob_filepath, 'wb') as f:
                f.write(enc_data)
            logger.debug(f"Wrote {len(enc_data)} bytes to {blob_filepath}")
        except Exception as e:
            logger.error(f"Failed to write torrent data to disk: {e}")
            traceback.print_exc() # ADD THIS LINE
            return None, None

        try:
            fs = lt.file_storage()
            fs.add_file(blob_filename, len(enc_data))
            t = lt.create_torrent(fs)
            t.add_tracker("udp://tracker.opentrackr.org:1337/announce")
            t.set_creator('Axon BBS')
            t.set_comment(json.dumps(metadata))
            
            lt.set_piece_hashes(t, self.torrent_save_path)
            
            torrent_dict = t.generate()

            if 'info' not in torrent_dict:
                logger.error(f"Failed to generate 'info' dictionary for torrent '{name}'. Hashing might have failed.")
                os.remove(blob_filepath)
                return None, None

            torrent_file_data = lt.bencode(torrent_dict)
            info = lt.torrent_info(torrent_file_data)
            
            params = {'ti': info, 'save_path': self.torrent_save_path}
            self.session.add_torrent(params)
            logger.info(f"Added torrent '{info.name()}' to session for seeding.")

            magnet = lt.make_magnet_uri(info)
            return magnet, torrent_file_data
        except Exception as e:
            logger.error(f"An unexpected error occurred during torrent creation: {e}", exc_info=True)
            traceback.print_exc() # ADD THIS LINE
            if os.path.exists(blob_filepath):
                os.remove(blob_filepath)
            return None, None

    # ... (All other methods remain the same) ...
