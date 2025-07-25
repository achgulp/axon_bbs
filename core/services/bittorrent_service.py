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

from core.models import TrustedInstance

logger = logging.getLogger(__name__)

class BitTorrentService:
    def __init__(self, tor_service):
        self.tor_service = tor_service
        self.local_onion = self.get_local_onion()
        self.private_key: RSAPrivateKey = self.load_bbs_private_key()

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

        # Auto-add peers from TrustedInstance.onion_url
        self.add_trusted_peers()

    def get_local_onion(self):
        """Read local .onion from Tor hidden service dir."""
        hidden_dir = '/var/lib/tor/bbs_hidden_service/'
        hostname_file = os.path.join(hidden_dir, 'hostname')
        if os.path.exists(hostname_file):
            with open(hostname_file, 'r') as f:
                return f.read().strip()
        return None

    def load_bbs_private_key(self):
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        local_instance = None
        if self.local_onion:
            local_instance = TrustedInstance.objects.filter(onion_url__contains=self.local_onion).first()
        if not local_instance:
            local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).exclude(encrypted_private_key='').first()
        
        if local_instance and local_instance.encrypted_private_key:
            try:
                private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
                return load_pem_private_key(private_pem.encode(), password=None)
            except InvalidToken as e:
                logger.warning(f"Invalid decryption for encrypted_private_key - regenerating keys: {e}")

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

        if not local_instance:
            local_instance = TrustedInstance.objects.create(
                onion_url=f"http://{self.local_onion}:8000" if self.local_onion else "",
                pubkey=public_key_pem,
                encrypted_private_key=encrypted_private
            )
        else:
            local_instance.pubkey = public_key_pem
            local_instance.encrypted_private_key = encrypted_private
            local_instance.save()
        
        logger.info(f"Loaded/Generated keys for instance: {local_instance.onion_url}")
        return private_key

    def add_trusted_peers(self):
        local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).exclude(encrypted_private_key='').first()
        if local_instance:
            trusted_peers = TrustedInstance.objects.exclude(pk=local_instance.pk)
        else:
            trusted_peers = TrustedInstance.objects.all()

        for peer in trusted_peers:
            if not peer.onion_url: continue
            
            url_parts = peer.onion_url.replace('http://', '').replace('https://', '').split(':')
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 6881
            
            logger.info(f"Noting trusted peer for future connections: {host}:{port}")

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
        temp_dir = os.path.join(settings.BASE_DIR, 'data', 'temp_torrents')
        os.makedirs(temp_dir, exist_ok=True)
        
        chunks = self.chunk_data(data)
        encrypted_chunks = []
        envelopes_list = []
        signatures = []

        trusted_pubkeys = list(TrustedInstance.objects.values_list('pubkey', flat=True))

        for chunk in chunks:
            aes_key, enc_chunk = self.encrypt_chunk(chunk)
            envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys if pk}
            
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            sig = self.private_key.sign(chunk_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
            
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
            aes_key = self.private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )

            trusted_pubkeys = TrustedInstance.objects.exclude(pubkey=my_pubkey).values_list('pubkey', flat=True)
            new_envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys if pk}
            new_envelopes_list.append(new_envelopes)

        metadata['envelopes'] = new_envelopes_list
        
        # Create a new torrent info object with the updated metadata
        fs = lt.file_storage()
        lt.add_files(fs, full_path)
        new_t = lt.create_torrent(fs)
        new_t.set_creator('AxonBBS v8.4.0 (re-seeded)')
        lt.set_piece_hashes(new_t, os.path.dirname(full_path))
        new_t.set_comment(json.dumps(metadata))
        
        new_torrent_file = lt.bencode(new_t.generate())
        new_magnet = lt.make_magnet_uri(lt.torrent_info(new_torrent_file))
        
        # Add the new torrent to the session to seed it
        self.session.add_torrent({'ti': lt.torrent_info(new_torrent_file), 'save_path': save_path})
        
        return new_magnet

    def download_and_decrypt(self, magnet, save_path, my_pubkey):
        params = {'url': magnet, 'save_path': save_path}
        handle = self.session.add_torrent(params)
        
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
            aes_key = self.private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            f = Fernet(aes_key)
            dec_chunk = f.decrypt(enc_chunk)
            decrypted_chunks.append(dec_chunk)

        return handle, b''.join(decrypted_chunks)
