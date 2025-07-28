# Full path: axon_bbs/core/services/bittorrent_service.py
import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
from cryptography.hazmat.primitives.serialization import load_pem_public_key
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
        blob_filename = f"{sanitized_name}_{uuid.uuid4().hex[:12]}.dat"
        blob_filepath = os.path.join(self.torrent_save_path, blob_filename)
        
        enc_data, metadata = self.encrypt_and_wrap(data)
        try:
            with open(blob_filepath, 'wb') as f:
                f.write(enc_data)
        except Exception as e:
            logger.error(f"Failed to write torrent data to disk: {e}")
            return None, None

        try:
            fs = lt.file_storage()
            fs.add_file(blob_filename, len(enc_data))
            t = lt.create_torrent(fs)
            t.add_tracker("udp://tracker.opentrackr.org:1337/announce")
            t.set_creator('Axon BBS')
            t.set_comment(json.dumps(metadata))
            
            # Add this instance's own .onion URL as a web seed before hashing
            local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
            if local_instance and local_instance.web_ui_onion_url:
                info_hash_hex_for_url = lt.sha1_hash(lt.bencode(t.generate()[b'info'])).hex()
                web_seed_url = f"{local_instance.web_ui_onion_url.strip('/')}/api/torrents/{info_hash_hex_for_url}/{blob_filename}"
                t.add_url_seed(web_seed_url)

            lt.set_piece_hashes(t, self.torrent_save_path)
            
            torrent_dict = t.generate()

            if b'info' not in torrent_dict:
                logger.error(f"Failed to generate 'info' dictionary for torrent '{name}'.")
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
            if os.path.exists(blob_filepath):
                os.remove(blob_filepath)
            return None, None

    def encrypt_and_wrap(self, data):
        chunks = self.chunk_data(data)
        enc_chunks = []
        envelopes_list = []
        trusted_pubkeys = [inst.pubkey for inst in TrustedInstance.objects.filter(is_trusted_peer=True) if inst.pubkey]
        
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        if local_instance and local_instance.pubkey and local_instance.pubkey not in trusted_pubkeys:
            trusted_pubkeys.append(local_instance.pubkey)
            
        for chunk in chunks:
            aes_key, enc_chunk = self.encrypt_chunk(chunk)
            enc_chunks.append(enc_chunk)
            envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys}
            envelopes_list.append(envelopes)
        enc_data = b''.join(enc_chunks)
        metadata = {'envelopes': envelopes_list}
        return enc_data, metadata

    def download_and_decrypt(self, magnet, save_path, my_pubkey):
        params = lt.parse_magnet_uri(magnet)
        params.save_path = save_path
        handle = self.session.add_torrent(params)
        start_time = time.time()
        
        while not handle.has_metadata():
            if time.time() - start_time > 60:
                logger.warning(f"Timeout waiting for metadata for torrent {handle.name()}.")
                return None, None
            s = handle.status()
            logger.debug(f"Status: {s.state}, Progress: {s.progress*100:.2f}%, Seeds: {s.num_seeds} (web: {s.num_web_seeds}), Peers: {s.num_peers}")
            time.sleep(2)

        logger.info(f"Metadata received for torrent: {handle.name()}. Starting download.")
        while not handle.status().is_seeding:
            if time.time() - start_time > 180:
                 logger.warning(f"Torrent {handle.name()} did not complete download in time.")
                 return None, None
            s = handle.status()
            logger.debug(f"Status: {s.state}, Progress: {s.progress*100:.2f}%, Seeds: {s.num_seeds} (web: {s.num_web_seeds}), Peers: {s.num_peers}")
            time.sleep(2)
        
        logger.info(f"Download complete for torrent: {handle.name()}.")
        ti = handle.torrent_file()
        if not ti:
            return handle, None
            
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']
        
        filename_in_torrent = ti.files().file_path(0)
        file_path = os.path.join(handle.save_path(), filename_in_torrent)
        
        with open(file_path, 'rb') as f:
            enc_data = f.read()
        chunks = self.chunk_data(enc_data)
        decrypted_chunks = []
        private_key = self.get_private_key()
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]
            encrypted_aes_b64 = envelopes.get(my_pubkey)
            if not encrypted_aes_b64:
                logger.error(f"My pubkey not in envelope for chunk {i}. Cannot decrypt.")
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
