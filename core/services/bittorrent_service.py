# axon_bbs/core/services/bittorrent_service.py
import libtorrent as lt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import os
import base64
import json
from core.models import TrustedInstance
from asgiref.sync import sync_to_async
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class BitTorrentService:
    def __init__(self, tor_service=None):
        settings_pack = {
            'listen_interfaces': '0.0.0.0:6881',
            'enable_dht': True,
            'proxy_hostname': '127.0.0.1',
            'proxy_port': 9050,
            'proxy_type': lt.proxy_type_t.socks5,
            'anonymous_mode': True,
            'alert_mask': lt.alert.category_t.all_categories  # Enable all for monitoring
        }
        self.session = lt.session(settings_pack)
        self.private_key = self.load_bbs_private_key()
        self.tor_service = tor_service

        # Load local .onion for self-exclusion
        self.local_onion = self.get_local_onion()

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
        # Load/generate RSA private key (store encrypted in DB)
        return rsa.generate_private_key(65537, 2048)  # Placeholder; load real

    def add_trusted_peers(self):
        trusted_onions = TrustedInstance.objects.values_list('onion_url', flat=True)
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

            self.session.add_dht_router(host, port)
            logger.info(f"Added trusted peer: {host}:{port}")

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
        pubkey = serialization.load_pem_public_key(pubkey_pem.encode())
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
        t.set_creator('AxonBBS v8.2.0')
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
