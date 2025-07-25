# axon_bbs/core/services/bittorrent_service.py
import libtorrent as lt
import asyncio
import base64
import json
import logging
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
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
        hidden_dir = '/var/lib/tor/bbs_hidden_service/'  # Match your torrc
        hostname_file = os.path.join(hidden_dir, 'hostname')
        if os.path.exists(hostname_file):
            with open(hostname_file, 'r') as f:
                return f.read().strip()
        return None  # If not set, no exclusion

    def load_bbs_private_key(self):
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])  # Derive Fernet key
        f = Fernet(key)
        local_instance = None
        if self.local_onion:
            local_instance = TrustedInstance.objects.filter(onion_url__contains=self.local_onion).first()
        if not local_instance:
            # Fallback: Look for any instance with encrypted_private_key (assume single local)
            local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
        if local_instance and local_instance.encrypted_private_key:
            try:
                private_pem = f.decrypt(local_instance.encrypted_private_key.encode()).decode()
                return load_pem_private_key(private_pem.encode(), password=None)
            except InvalidToken as e:
                logger.warning(f"Invalid decryption for encrypted_private_key - regenerating keys: {e}")
                # Fall through to generation below
        # Generate new if not exist or invalid
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key().public_bytes(
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
                onion_url=f"http://{self.local_onion}:6881" if self.local_onion else "",
                pubkey=public_key,
                encrypted_private_key=encrypted_private
            )
        else:
            local_instance.pubkey = public_key
            local_instance.encrypted_private_key = encrypted_private
            local_instance.save()
        return private_key

    def add_trusted_peers(self):
        trusted_onions = TrustedInstance.objects.filter(encrypted_private_key='').values_list('onion_url', flat=True)  # Exclude local (assumed to have private key)
        for onion in trusted_onions:
            # Parse host and port safely
            if '://' in onion:
                onion = onion.split('://')[1]  # Remove http:// or wss://
            if ':' in onion:
                host, port_str = onion.split(':')
                port = int(port_str)
            else:
                host = onion
                port = 6881  # Default if no port

            # Exclude self if local .onion matches
            if self.local_onion and host == self.local_onion:
                logger.info(f"Skipping self as peer: {host}:{port}")
                continue

            # Since DHT is disabled, add as direct peers if possible (libtorrent doesn't have direct add_node, but we can log or prepare for torrent params)
            logger.info(f"Trusted peer noted (DHT disabled): {host}:{port}")

    async def start_session(self):
        # Async loop for session management (e.g., alerts)
        while True:
            alerts = self.session.pop_alerts()
            for a in alerts:
                logger.info(f"BitTorrent Alert: {a.message()} ({a.what()})")  # Log all alerts
            await asyncio.sleep(1)

    def chunk_data(self, data, chunk_size=1024*1024):  # 1MB chunks
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

    def create_torrent(self, data, file_path):
        chunks = self.chunk_data(data)
        encrypted_chunks = []
        envelopes_list = []
        signatures = []

        trusted_pubkeys = TrustedInstance.objects.values_list('pubkey', flat=True)  # PEM strings

        for chunk in chunks:
            aes_key, enc_chunk = self.encrypt_chunk(chunk)
            envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys}
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            sig = self.private_key.sign(chunk_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
            signatures.append(base64.b64encode(sig).decode())

            encrypted_chunks.append(enc_chunk)
            envelopes_list.append(envelopes)

        enc_data = b''.join(encrypted_chunks)
        with open(file_path + '.enc', 'wb') as f:
            f.write(enc_data)

        fs = lt.file_storage()
        fs.add_file(os.path.basename(file_path) + '.enc', len(enc_data))
        t = lt.create_torrent(fs)
        t.set_creator('AxonBBS v8.3.0')
        lt.set_piece_hashes(t, '.')
        metadata = {'envelopes': envelopes_list, 'signatures': signatures}
        t.set_comment(json.dumps(metadata))
        torrent_file = lt.bencode(t.generate())
        magnet = lt.make_magnet_uri(lt.torrent_info(torrent_file))
        return magnet, torrent_file

    def re_envelope_and_reseed(self, torrent_handle, save_path, my_pubkey):
        ti = torrent_handle.torrent_file()
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']
        signatures = metadata['signatures']

        enc_data = open(os.path.join(save_path, ti.files().file_path(0)), 'rb').read()
        chunks = self.chunk_data(enc_data)

        new_envelopes_list = []
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]

            # Decrypt AES key from my envelope
            encrypted_aes = base64.b64decode(envelopes.get(my_pubkey))
            aes_key = self.private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )

            # Re-envelope for my trusts (remove others)
            trusted_pubkeys = TrustedInstance.objects.values_list('pubkey', flat=True)
            new_envelopes = {pk: self.create_envelope(aes_key, pk) for pk in trusted_pubkeys if pk != my_pubkey}
            new_envelopes_list.append(new_envelopes)

            # Verify sig
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            # sender_pub = ...  # Load from trusted or metadata
            # sender_pub.verify(base64.b64decode(signatures[i]), chunk_hash, ...)

        # Update metadata and re-create torrent
        metadata['envelopes'] = new_envelopes_list
        ti.set_comment(json.dumps(metadata))
        new_torrent = lt.bencode(ti.generate())

        # Re-seed
        self.session.add_torrent({'ti': lt.torrent_info(new_torrent), 'save_path': save_path})
        new_magnet = lt.make_magnet_uri(lt.torrent_info(new_torrent))
        return new_magnet  # Share with trusts

    def download_and_decrypt(self, magnet, save_path, my_pubkey):
        params = {'url': magnet, 'save_path': save_path}
        handle = self.session.add_torrent(params)
        while not handle.is_seed():
            s = handle.status()
            print(f"Progress: {s.progress * 100:.2f}%")

        ti = handle.torrent_file()
        metadata = json.loads(ti.comment())
        envelopes_list = metadata['envelopes']
        signatures = metadata['signatures']

        enc_data = open(os.path.join(save_path, ti.files().file_path(0)), 'rb').read()
        chunks = self.chunk_data(enc_data)

        decrypted_chunks = []
        for i, enc_chunk in enumerate(chunks):
            envelopes = envelopes_list[i]
            encrypted_aes = base64.b64decode(envelopes.get(my_pubkey))
            if not encrypted_aes:
                raise ValueError("No envelope for this BBS")

            aes_key = self.private_key.decrypt(
                encrypted_aes,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            f = Fernet(aes_key)
            dec_chunk = f.decrypt(enc_chunk)

            # Verify signature
            chunk_hash_ctx = hashes.Hash(hashes.SHA256())
            chunk_hash_ctx.update(enc_chunk)
            chunk_hash = chunk_hash_ctx.finalize()
            # sender_pub.verify(base64.b64decode(signatures[i]), chunk_hash, ...)

            decrypted_chunks.append(dec_chunk)

        return b''.join(decrypted_chunks)
