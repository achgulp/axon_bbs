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
        self._private_key = None
        self._trusted_peers = None
        
        settings_pack = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'dht_bootstrap_nodes': '', 
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
        self.bootstrap_private_dht()

    def bootstrap_private_dht(self):
        try:
            peers = TrustedInstance.objects.values_list('p2p_onion_address', flat=True)
            for peer_addr in peers:
                if peer_addr and ':' in peer_addr:
                    try:
                        host, port_str = peer_addr.split(':')
                        self.session.add_dht_router(host, int(port_str))
                        logger.info(f"Added trusted peer to DHT bootstrap: {host}:{port_str}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid P2P address format for DHT bootstrap: {peer_addr}")
        except OperationalError:
            logger.warning("Could not bootstrap DHT, database may not be ready.")

    def get_private_key(self):
        if self._private_key is None:
            try:
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                f = Fernet(key)
                local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).exclude(encrypted_private_key='').first()
                if local_instance and local_instance.encrypted_private_key:
                    private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
                    self._private_key = load_pem_private_key(private_pem.encode(), password=None)
            except (OperationalError, InvalidToken) as e:
                logger.error(f"DATABASE/DECRYPTION ERROR: Could not load private key: {e}.")
                return None
        return self._private_key

    async def start_session(self):
        while True:
            alerts = self.session.pop_alerts()
            for a in alerts:
                if isinstance(a, lt.dht_stats_alert):
                    logger.info(f"DHT stats: {a.active_nodes} active nodes.")
                else:
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
        enc_file_path = os.path.join(temp_dir, f"{file_name}_{int(time.time())}.enc")
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
        
        params = lt.add_torrent_params()
        params.ti = lt.torrent_info(torrent_file)
        params.save_path = temp_dir
        self.session.add_torrent(params)

        return magnet, enc_file_path

    def download_and_decrypt(self, magnet, save_path, my_pubkey):
        params = lt.parse_magnet_uri(magnet)
        params.save_path = save_path
        handle = self.session.add_torrent(params)
        private_key = self.get_private_key()
        
        logger.info(f"Downloading torrent {handle.name()}. Waiting for DHT and peers...")
        for _ in range(120):
            s = handle.status()
            if s.is_seeding or s.progress == 1.0:
                logger.info("Download complete.")
                break
            dht_nodes = self.session.status().dht_nodes
            logger.debug(f"Status: {s.state}, Peers: {s.num_peers}, DHT Nodes: {dht_nodes}, Progress: {s.progress*100:.2f}%")
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
