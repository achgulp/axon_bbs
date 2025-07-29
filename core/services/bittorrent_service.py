# Full path: axon_bbs/core/services/bittorrent_service.py
import os
import logging
import libtorrent as lt
import time
import json
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
from django.conf import settings
from django.utils import timezone

# These imports need to be relative for Django's resolver
from .encryption_utils import generate_checksum
from .tor_service import TorService
from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class BitTorrentService:
    def __init__(self, tor_service=None):
        """Initialize the BitTorrent service with an optional Tor service."""
        self.session = None
        self.torrents = {}
        self.save_path = os.path.join(settings.BASE_DIR, 'data', 'torrents')
        os.makedirs(self.save_path, exist_ok=True)
        self.tor_service = tor_service
        self.initialize_session()

    def initialize_session(self):
        """Initialize the libtorrent session with Tor proxy settings."""
        try:
            logger.info(f"Using libtorrent version: {lt.version}")

            # Create a settings pack object. This is the robust, version-safe way
            # to configure the session, avoiding KeyErrors with string-based keys.
            sp = lt.settings_pack()

            # Set standard options
            sp.set_bool(lt.settings_pack.enable_dht, True)
            sp.set_bool(lt.settings_pack.anonymous_mode, True)
            sp.set_bool(lt.settings_pack.announce_to_all_tiers, True)
            sp.set_bool(lt.settings_pack.announce_to_all_trackers, True)
            sp.set_str(lt.settings_pack.listen_interfaces, '0.0.0.0:6881')

            # Set proxy settings using the official API
            sp.set_int(lt.settings_pack.proxy_type, lt.proxy_type_t.socks5)
            sp.set_str(lt.settings_pack.proxy_hostname, '127.0.0.1')
            proxy_port = 9050 if not self.tor_service else self.tor_service.get_proxy_port()
            sp.set_int(lt.settings_pack.proxy_port, proxy_port)
            
            # These settings ensure all types of traffic are routed via the proxy.
            # The 'proxy_dht' key that caused the error is not needed here;
            # DHT traffic is proxied when peer connections are proxied.
            sp.set_bool(lt.settings_pack.proxy_peer_connections, True)
            sp.set_bool(lt.settings_pack.proxy_tracker_connections, True)

            # Initialize the session and apply the settings
            self.session = lt.session()
            self.session.apply_settings(sp)
            
            # Add DHT routers for bootstrapping the network
            self.session.add_dht_router('router.bittorrent.com', 6881)
            self.session.add_dht_router('dht.transmissionbt.com', 6881)
            self.session.start_dht()

            logger.info(f"BitTorrent session initialized with Tor proxy at 127.0.0.1:{proxy_port}.")

        except Exception as e:
            logger.error(f"Failed to initialize BitTorrent session: {e}. Check libtorrent installation.", exc_info=True)
            raise

    def get_private_key(self):
        """Retrieve the unencrypted private key from the local instance."""
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        if not local_instance or not local_instance.encrypted_private_key:
            logger.warning("No local instance identity found.")
            return None
        
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        from cryptography.fernet import Fernet
        f = Fernet(key)
        try:
            private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
            return serialization.load_pem_private_key(private_pem.encode(), password=None)
        except Exception as e:
            logger.error(f"Failed to decrypt private key: {e}")
            return None

    def create_torrent(self, data, name_prefix):
        """Create a torrent from encrypted data for a message."""
        aes_key = os.urandom(32)
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        
        padded_data = data + b'\0' * (16 - len(data) % 16)
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        fs = lt.file_storage()
        file_entry_name = f"{name_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"
        fs.add_file(file_entry_name, len(encrypted_data))

        t = lt.create_torrent(fs)
        # Updated version string
        t.set_creator('Axon BBS v9.0.1')
        lt.set_piece_hashes(t, '.')
        
        torrent_data = t.generate()
        info_hash = torrent_data['info_hash']

        magnet_link = lt.make_magnet_uri(lt.torrent_info(torrent_data))
        
        self.torrents[info_hash] = {"data": encrypted_data, "key": aes_key, "iv": iv}
        
        return magnet_link, encrypted_data

    def download_and_decrypt(self, magnet, save_path, peer_pubkey):
        """Download and decrypt a torrent."""
        try:
            params = lt.parse_magnet_uri(magnet)
            params.save_path = save_path
            handle = self.session.add_torrent(params)
            
            logger.info(f"Downloading magnet: {magnet[:50]}...")
            
            while not handle.status().is_seeding:
                time.sleep(1)

            logger.info("Download complete. Decrypting...")
            
            info = handle.get_torrent_info()
            file_path = os.path.join(save_path, info.files().file_path(0))
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

            torrent_info = self.torrents.get(info.info_hash())
            if not torrent_info:
                logger.error(f"No key found for torrent hash: {info.info_hash()}")
                return None, None
            
            aes_key = torrent_info['key']
            iv = torrent_info['iv']

            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            data = padded_data.rstrip(b'\0')
            
            return handle, data
        except Exception as e:
            logger.error(f"Failed to download/decrypt torrent: {e}", exc_info=True)
            return None, None

    def start(self):
        """Start the BitTorrent service thread."""
        threading.Thread(target=self._run, daemon=True).start()
        logger.info("BitTorrent service thread started.")

    def _run(self):
        """The main loop for the service to process alerts."""
        while True:
            try:
                alerts = self.session.pop_alerts()
                for a in alerts:
                    if isinstance(a, lt.metadata_received_alert):
                        logger.info(f"Metadata received for torrent: {a.torrent_name()}")
                    elif isinstance(a, lt.torrent_finished_alert):
                        logger.info(f"Torrent finished: {a.torrent_name()}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in BitTorrent service loop: {e}", exc_info=True)

