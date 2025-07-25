# axon_bbs/core/services/bittorrent_service.py
import libtorrent as lt
import asyncio
import base64
import json
import logging
import os
import time
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from django.conf import settings
from django.db import OperationalError

from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class BitTorrentService:
    def __init__(self, tor_service):
        self.tor_service = tor_service
        self._private_key = None # Will be loaded lazily# axon_bbs/core/services/bittorrent_service.py
import libtorrent as lt
import asyncio
import base64
import json
import logging
import os
import time
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from django.conf import settings
from django.db import OperationalError

from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class BitTorrentService:
    def __init__(self, tor_service):
        self.tor_service = tor_service
        self._private_key = None # Will be loaded lazily
        self._trusted_peers = None # Will be loaded lazily
        
        # Initialize libtorrent session with Tor proxy
        settings_pack = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': False,
            'enable_lsd': False,
            'proxy_hostname': self.tor_service._socks_host,
            'proxy_port': self.tor_service._socks_port,
            'proxy_type': lt.proxy_type_t.socks5,
            'proxy_peer_connections': True,
            'proxy_tracker_connections': True,
            'proxy_hostnames': True,
            'anonymous_mode': True
        }
        self.session = lt.session(settings_pack)

    def get_local_onion(self):
        """Read local .onion from Tor hidden service dir."""
        hidden_dir = '/var/lib/tor/bbs_hidden_service/'
        hostname_file = os.path.join(hidden_dir, 'hostname')
        if os.path.exists(hostname_file):
            with open(hostname_file, 'r') as f:
                return f.read().strip()
        return None

    def get_private_key(self):
        """
        Lazily loads the BBS private key from the database.
        Caches the key after the first load.
        """
        if self._private_key is None:
            try:
                local_onion = self.get_local_onion()
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                f = Fernet(key)
                local_instance = None
                if local_onion:
                    local_instance = TrustedInstance.objects.filter(web_ui_onion_url__contains=local_onion).first()
                if not local_instance:
                    local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).exclude(encrypted_private_key='').first()
                
                if local_instance and local_instance.encrypted_private_key:
                    private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
                    self._private_key = load_pem_private_key(private_pem.encode(), password=None)
                else: # Fallback to generate a new key if none exists
                    logger.warning("No existing private key found in DB. Generating a new one.")
                    private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                    public_key_pem = private_key_obj.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
                    private_pem = private_key_obj.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode('utf-8')
                    encrypted_private = f.encrypt(private_pem.encode()).decode()
                    if not local_instance:
                        local_instance = TrustedInstance.objects.create(web_ui_onion_url=f"http://{local_onion}" if local_onion else "", pubkey=public_key_pem, encrypted_private_key=encrypted_private)
                    else:
                        local_instance.pubkey = public_key_pem
                        local_instance.encrypted_private_key = encrypted_private
                        local_instance.save()
                    self._private_key = private_key_obj
            except (OperationalError, InvalidToken) as e:
                logger.error(f"DATABASE/DECRYPTION ERROR: Could not load private key: {e}. Posting will fail.")
                return None
        return self._private_key

    def get_trusted_peers(self):
        """Lazily loads the list of trusted peer public keys."""
        if self._trusted_peers is None:
            try:
                self._trusted_peers = list(TrustedInstance.objects.values_list('pubkey', flat=True))
            except OperationalError as e:
                logger.error(f"DATABASE ERROR: Could not load trusted peers: {e}.")
                self._trusted_peers = []
        return self._trusted_peers

    async def start_session(self):
        while True:
            alerts = self.session.pop_alerts()
            for a in alerts:
                logger.info(f"BitTorrent Alert: {a.message()} ({a.what()})")
            await asyncio.sleep(1)

    def chunk_data(self, data, chunk_size=256*1024):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def encrypt_chunk(self, chunk):
        aes_key = Fernet.generate_key()
        f = Fernet(aes_key)
        encrypted_chunk = f.encrypt(chunk)
        return aes_key, encrypted_chunk

    def create_envelope(self, aes_key, pubkey_pem):
        pubkey = load_pem_public_key(pubkey_pem.encode())
        encrypted_aes = pubkey.encrypt(
            aes_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        return base64.b64encode(encrypted_aes).decode()

    def create_torrent(self, data: bytes, file_name: str):
        private_key = self.get_private_key()
        if not private_key:
            raise Exception("Cannot create torrent: BBS private key is not loaded.")

        temp_dir = os.path.join(settings.BASE_DIR, 'data', 'temp_torrents')
        os.makedirs(temp_dir, exist_ok=True)
        
        chunks = self.chunk_data(data)
        encrypted_chunks = []
        envelopes_list = []
        signatures = []

        trusted_pubkeys = self.get_trusted_peers()

        for chunk in chunks:
            aes_key, enc_chunk = self.encrypt_chunk(chunk)
            envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys if pk}
            
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            sig = private_key.sign(chunk_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
            
            signatures.append(base64.b64encode(sig).decode())
            encrypted_chunks.append(enc_chunk)
            envelopes_list.append(envelopes)

        enc_data = b''.join(encrypted_chunks)
        enc_file_path = os.path.join(temp_dir, file_name + '.enc')
        with open(enc_file_path, 'wb') as f:
            f.write(enc_data)

        fs = lt.file_storage()
        lt.add_files(fs, enc_file_path)
        t = lt.create_torrent(fs)
        t.set_creator('AxonBBS v8.4.0')
        lt.set_piece_hashes(t, os.path.dirname(enc_file_path))
        metadata = {'envelopes': envelopes_list, 'signatures': signatures}
        t.set_comment(json.dumps(metadata))
        torrent_file = lt.bencode(t.generate())
        magnet = lt.make_magnet_uri(lt.torrent_info(torrent_file))
        
        self.session.add_torrent({'ti': lt.torrent_info(torrent_file), 'save_path': temp_dir})

        return magnet, torrent_file

    def re_envelope_and_reseed(self, torrent_handle, save_path, my_pubkey):
        ti = torrent_handle.torrent_file()
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']
        private_key = self.get_private_key()

        full_path = os.path.join(save_path, ti.files().file_path(0))
        with open(full_path, 'rb') as f:
            enc_data = f.read()
        chunks = self.chunk_data(enc_data)

        new_envelopes_list = []
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]

            encrypted_aes_b64 = envelopes.get(my_pubkey)
            if not encrypted_aes_b64: continue
            
            encrypted_aes = base64.b64decode(encrypted_aes_b64)
            aes_key = private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )

            # Re-envelope for peers other than myself
            other_peers_pubkeys = [pk for pk in self.get_trusted_peers() if pk != my_pubkey]
            new_envelopes = {pk: self.create_envelope(aes_key, pk) for pk in other_peers_pubkeys if pk}
            new_envelopes_list.append(new_envelopes)

        metadata['envelopes'] = new_envelopes_list
        
        fs = lt.file_storage()
        lt.add_files(fs, full_path)
        new_t = lt.create_torrent(fs)
        new_t.set_creator('AxonBBS v8.4.0 (re-seeded)')
        lt.set_piece_hashes(new_t, os.path.dirname(full_path))
        new_t.set_comment(json.dumps(metadata))
        
        new_torrent_file = lt.bencode(new_t.generate())
        new_magnet = lt.make_magnet_uri(lt.torrent_info(new_torrent_file))
        
        self.session.add_torrent({'ti': lt.torrent_info(new_torrent_file), 'save_path': save_path})
        
        return new_magnet

    def download_and_decrypt(self, magnet, save_path, my_pubkey, peer_address=None):
        params = {'url': magnet, 'save_path': save_path}
        handle = self.session.add_torrent(params)
        private_key = self.get_private_key()

        if peer_address and ':' in peer_address:
            try:
                host, port_str = peer_address.split(':')
                port = int(port_str)
                handle.connect_peer((host, port))
                logger.info(f"Connecting directly to peer {host}:{port}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid peer address format '{peer_address}': {e}")
        
        for _ in range(120): # Wait up to 2 minutes
            s = handle.status()
            if s.is_seeding:
                break
            time.sleep(1)
        else:
            logger.warning(f"Torrent {handle.name()} did not complete download in time.")
            return None, None

        ti = handle.torrent_file()
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']

        file_path = os.path.join(save_path, ti.files().file_path(0))
        with open(file_path, 'rb') as f:
            enc_data = f.read()

        chunks = self.chunk_data(enc_data)
        decrypted_chunks = []
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]
            encrypted_aes_b64 = envelopes.get(my_pubkey)
            if not encrypted_aes_b64:
                return handle, None

            encrypted_aes = base64.b64decode(encrypted_aes_b64)
            aes_key = private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            f = Fernet(aes_key)
            dec_chunk = f.decrypt(enc_chunk)
            decrypted_chunks.append(dec_chunk)

        return handle, b''.join(decrypted_chunks)
        self._trusted_peers = None # Will be loaded lazily
        
        # Initialize libtorrent session with Tor proxy
        settings_pack = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': False,
            'enable_lsd': False,
            'proxy_hostname': self.tor_service._socks_host,
            'proxy_port': self.tor_service._socks_port,
            'proxy_type': lt.proxy_type_t.socks5,
            'proxy_peer_connections': True,
            'proxy_tracker_connections': True,
            'proxy_hostnames': True,
            'anonymous_mode': True
        }
        self.session = lt.session(settings_pack)

    def get_local_onion(self):
        """Read local .onion from Tor hidden service dir."""
        hidden_dir = '/var/lib/tor/bbs_hidden_service/'
        hostname_file = os.path.join(hidden_dir, 'hostname')
        if os.path.exists(hostname_file):
            with open(hostname_file, 'r') as f:
                return f.read().strip()
        return None

    def get_private_key(self):
        """
        Lazily loads the BBS private key from the database.
        Caches the key after the first load.
        """
        if self._private_key is None:
            try:
                local_onion = self.get_local_onion()
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                f = Fernet(key)
                local_instance = None
                if local_onion:
                    local_instance = TrustedInstance.objects.filter(web_ui_onion_url__contains=local_onion).first()
                if not local_instance:
                    local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).exclude(encrypted_private_key='').first()
                
                if local_instance and local_instance.encrypted_private_key:
                    private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
                    self._private_key = load_pem_private_key(private_pem.encode(), password=None)
                else: # Fallback to generate a new key if none exists
                    logger.warning("No existing private key found in DB. Generating a new one.")
                    private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                    public_key_pem = private_key_obj.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
                    private_pem = private_key_obj.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode('utf-8')
                    encrypted_private = f.encrypt(private_pem.encode()).decode()
                    if not local_instance:
                        local_instance = TrustedInstance.objects.create(web_ui_onion_url=f"http://{local_onion}" if local_onion else "", pubkey=public_key_pem, encrypted_private_key=encrypted_private)
                    else:
                        local_instance.pubkey = public_key_pem
                        local_instance.encrypted_private_key = encrypted_private
                        local_instance.save()
                    self._private_key = private_key_obj
            except (OperationalError, InvalidToken) as e:
                logger.error(f"DATABASE/DECRYPTION ERROR: Could not load private key: {e}. Posting will fail.")
                return None
        return self._private_key

    def get_trusted_peers(self):
        """Lazily loads the list of trusted peer public keys."""
        if self._trusted_peers is None:
            try:
                self._trusted_peers = list(TrustedInstance.objects.values_list('pubkey', flat=True))
            except OperationalError as e:
                logger.error(f"DATABASE ERROR: Could not load trusted peers: {e}.")
                self._trusted_peers = []
        return self._trusted_peers

    async def start_session(self):
        while True:
            alerts = self.session.pop_alerts()
            for a in alerts:
                logger.info(f"BitTorrent Alert: {a.message()} ({a.what()})")
            await asyncio.sleep(1)

    def chunk_data(self, data, chunk_size=256*1024):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def encrypt_chunk(self, chunk):
        aes_key = Fernet.generate_key()
        f = Fernet(aes_key)
        encrypted_chunk = f.encrypt(chunk)
        return aes_key, encrypted_chunk

    def create_envelope(self, aes_key, pubkey_pem):
        pubkey = load_pem_public_key(pubkey_pem.encode())
        encrypted_aes = pubkey.encrypt(
            aes_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        return base64.b64encode(encrypted_aes).decode()

    def create_torrent(self, data: bytes, file_name: str):
        private_key = self.get_private_key()
        if not private_key:
            raise Exception("Cannot create torrent: BBS private key is not loaded.")

        temp_dir = os.path.join(settings.BASE_DIR, 'data', 'temp_torrents')
        os.makedirs(temp_dir, exist_ok=True)
        
        chunks = self.chunk_data(data)
        encrypted_chunks = []
        envelopes_list = []
        signatures = []

        trusted_pubkeys = self.get_trusted_peers()

        for chunk in chunks:
            aes_key, enc_chunk = self.encrypt_chunk(chunk)
            envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys if pk}
            
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            sig = private_key.sign(chunk_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
            
            signatures.append(base64.b64encode(sig).decode())
            encrypted_chunks.append(enc_chunk)
            envelopes_list.append(envelopes)

        enc_data = b''.join(encrypted_chunks)
        enc_file_path = os.path.join(temp_dir, file_name + '.enc')
        with open(enc_file_path, 'wb') as f:
            f.write(enc_data)

        fs = lt.file_storage()
        lt.add_files(fs, enc_file_path)
        t = lt.create_torrent(fs)
        t.set_creator('AxonBBS v8.4.0')
        lt.set_piece_hashes(t, os.path.dirname(enc_file_path))
        metadata = {'envelopes': envelopes_list, 'signatures': signatures}
        t.set_comment(json.dumps(metadata))
        torrent_file = lt.bencode(t.generate())
        magnet = lt.make_magnet_uri(lt.torrent_info(torrent_file))
        
        self.session.add_torrent({'ti': lt.torrent_info(torrent_file), 'save_path': temp_dir})

        return magnet, torrent_file

    def re_envelope_and_reseed(self, torrent_handle, save_path, my_pubkey):
        ti = torrent_handle.torrent_file()
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']
        private_key = self.get_private_key()

        full_path = os.path.join(save_path, ti.files().file_path(0))
        with open(full_path, 'rb') as f:
            enc_data = f.read()
        chunks = self.chunk_data(enc_data)

        new_envelopes_list = []
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]

            encrypted_aes_b64 = envelopes.get(my_pubkey)
            if not encrypted_aes_b64: continue
            
            encrypted_aes = base64.b64decode(encrypted_aes_b64)
            aes_key = private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )

            # Re-envelope for peers other than myself
            other_peers_pubkeys = [pk for pk in self.get_trusted_peers() if pk != my_pubkey]
            new_envelopes = {pk: self.create_envelope(aes_key, pk) for pk in other_peers_pubkeys if pk}
            new_envelopes_list.append(new_envelopes)

        metadata['envelopes'] = new_envelopes_list
        
        fs = lt.file_storage()
        lt.add_files(fs, full_path)
        new_t = lt.create_torrent(fs)
        new_t.set_creator('AxonBBS v8.4.0 (re-seeded)')
        lt.set_piece_hashes(new_t, os.path.dirname(full_path))
        new_t.set_comment(json.dumps(metadata))
        
        new_torrent_file = lt.bencode(new_t.generate())
        new_magnet = lt.make_magnet_uri(lt.torrent_info(new_torrent_file))
        
        self.session.add_torrent({'ti': lt.torrent_info(new_torrent_file), 'save_path': save_path})
        
        return new_magnet

    def download_and_decrypt(self, magnet, save_path, my_pubkey, peer_address=None):
        params = {'url': magnet, 'save_path': save_path}
        handle = self.session.add_torrent(params)
        private_key = self.get_private_key()

        if peer_address and ':' in peer_address:
            try:
                host, port_str = peer_address.split(':')
                port = int(port_str)
                handle.connect_peer((host, port))
                logger.info(f"Connecting directly to peer {host}:{port}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid peer address format '{peer_address}': {e}")
        
        for _ in range(120): # Wait up to 2 minutes
            s = handle.status()
            if s.is_seeding:
                break
            time.sleep(1)
        else:
            logger.warning(f"Torrent {handle.name()} did not complete download in time.")
            return None, None

        ti = handle.torrent_file()
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']

        file_path = os.path.join(save_path, ti.files().file_path(0))
        with open(file_path, 'rb') as f:
            enc_data = f.read()

        chunks = self.chunk_data(enc_data)
        decrypted_chunks = []
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]
            encrypted_aes_b64 = envelopes.get(my_pubkey)
            if not encrypted_aes_b64:
                return handle, None

            encrypted_aes = base64.b64decode(encrypted_aes_b64)
            aes_key = private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            f = Fernet(aes_key)
            dec_chunk = f.decrypt(enc_chunk)
            decrypted_chunks.append(dec_chunk)

        return handle, b''.join(decrypted_chunks)
