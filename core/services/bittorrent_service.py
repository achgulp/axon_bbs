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
from manage import APP_VERSION

logger = logging.getLogger(__name__)

class BitTorrentService:
    def __init__(self, tor_service):
        self.tor_service = tor_service
        self._private_key = None
        self._trusted_peers = None
        
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
            'anonymous_mode': True,
            'user_agent': f'AxonBBS/{APP_VERSION} libtorrent/{lt.version}',
        }
        self.session = lt.session(settings_pack)

    def prime_identity(self):
        """A method to explicitly load or generate the key at startup."""
        logger.info("Priming BitTorrent service identity...")
        self.get_private_key()

    def get_private_key(self):
        if self._private_key is None:
            try:
                # This check might run before the DB is ready, so we need to be careful.
                local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).exclude(encrypted_private_key='').first()
                
                if local_instance and local_instance.encrypted_private_key:
                    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                    f = Fernet(key)
                    private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
                    self._private_key = load_pem_private_key(private_pem.encode(), password=None)
                    logger.info(f"Successfully loaded local instance key for instance ID {local_instance.id}.")
                else:
                    # This part runs if no key is found.
                    # It should have been triggered during startup priming.
                    # If we reach here during normal operation, something is wrong.
                    logger.warning("get_private_key() called but no key found in database.")
                    return None
            except OperationalError:
                logger.warning("Database is not ready yet for key loading. Will retry on next call.")
                return None
            except Exception as e:
                logger.error(f"CRITICAL ERROR in get_private_key: {e}", exc_info=True)
                return None
        return self._private_key

    async def start_session(self):
        while True:
            alerts = self.session.pop_alerts()
            for a in alerts:
                logger.info(f"BitTorrent Alert: {a.message()} ({a.what()})")
            await asyncio.sleep(5)

    def create_torrent(self, data: bytes, file_name: str):
        private_key = self.get_private_key()
        if not private_key:
            raise Exception("Cannot create torrent: BBS private key is not loaded.")

        temp_dir = os.path.join(settings.BASE_DIR, 'data', 'temp_torrents')
        os.makedirs(temp_dir, exist_ok=True)
        
        chunks = self.chunk_data(data)
        encrypted_chunks, envelopes_list, signatures = [], [], []
        trusted_pubkeys = list(TrustedInstance.objects.values_list('pubkey', flat=True))

        for chunk in chunks:
            aes_key, enc_chunk = self.encrypt_chunk(chunk)
            envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys if pk}
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            sig = private_key.sign(chunk_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
            signatures.append(base64.b64encode(sig).decode('utf-8'))
            encrypted_chunks.append(enc_chunk)
            envelopes_list.append(envelopes)
        enc_data = b''.join(encrypted_chunks)
        
        data_hash = hashes.Hash(hashes.SHA256())
        data_hash.update(enc_data)
        data_hash_hex = data_hash.finalize().hex()
        
        enc_file_path = os.path.join(temp_dir, f"{data_hash_hex}.enc")
        with open(enc_file_path, 'wb') as f:
            f.write(enc_data)

        fs = lt.file_storage()
        lt.add_files(fs, enc_file_path)
        
        t = lt.create_torrent(fs)
        t.set_creator('AxonBBS v8.4.0')
        lt.set_piece_hashes(t, os.path.dirname(enc_file_path))
        
        torrent_file_for_hash = lt.bencode(t.generate())
        info = lt.torrent_info(torrent_file_for_hash)
        info_hash_hex = info.info_hashes().v1.to_bytes().hex()
        
        trusted_peers = TrustedInstance.objects.all()
        for peer in trusted_peers:
            if peer.web_ui_onion_url:
                seed_url = f"{peer.web_ui_onion_url.strip('/')}/api/torrents/{info_hash_hex}/"
                t.add_url_seed(seed_url)
                logger.info(f"Adding web seed: {seed_url}")

        metadata = {'envelopes': envelopes_list, 'signatures': signatures}
        t.set_comment(json.dumps(metadata))
        
        final_torrent_file = lt.bencode(t.generate())
        magnet = lt.make_magnet_uri(lt.torrent_info(final_torrent_file))
        
        params = lt.add_torrent_params()
        params.ti = lt.torrent_info(final_torrent_file)
        params.save_path = temp_dir
        self.session.add_torrent(params)

        return magnet, enc_file_path

    def download_and_decrypt(self, magnet, save_path, my_pubkey):
        params = lt.parse_magnet_uri(magnet)
        params.save_path = save_path
        handle = self.session.add_torrent(params)
        private_key = self.get_private_key()
        
        logger.info(f"Downloading torrent {handle.name()}. Waiting for web seeds...")
        for _ in range(120): # Wait up to 2 minutes
            s = handle.status()
            if s.is_seeding or s.progress == 1.0:
                logger.info("Download complete.")
                break
            logger.debug(f"Status: {s.state}, Progress: {s.progress*100:.2f}%, Seeds: {s.num_seeds}")
            time.sleep(2)
        else:
            logger.warning(f"Torrent {handle.name()} did not complete download in time.")
            return None, None

        ti = handle.torrent_file()
        if not ti:
            return handle, None
            
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']
        file_entry = ti.files().file_path(0)
        file_path = os.path.join(save_path, file_entry)
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

    def chunk_data(self, data, chunk_size=256*1024): return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    def encrypt_chunk(self, chunk): aes_key = Fernet.generate_key(); f = Fernet(aes_key); return aes_key, f.encrypt(chunk)
    def create_envelope(self, aes_key, pubkey_pem): pubkey = load_pem_public_key(pubkey_pem.encode()); return base64.b64encode(pubkey.encrypt(aes_key, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))).decode('utf-8')
    def re_envelope_and_reseed(self, torrent_handle, save_path, my_pubkey): pass
