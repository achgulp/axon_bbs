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


# Full path: axon_bbs/core/management/commands/compare_sync_status.py
import requests
import base64
import hashlib
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.conf import settings
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.fernet import Fernet

from core.models import TrustedInstance, FileAttachment
from messaging.models import Message

class Command(BaseCommand):
    help = 'Compares local content with a remote peer to see what needs to be synced.'

    def add_arguments(self, parser):
        parser.add_argument('peer_onion_url', type=str, help="The full .onion URL of the peer to compare against.")

    def _load_identity(self):
        """Loads the local instance's private key."""
        try:
            local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()
            if not (local_instance and local_instance.encrypted_private_key):
                raise ValueError("Local instance with private key not found.")
            
            key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
            f = Fernet(key)
            decrypted_pem = f.decrypt(local_instance.encrypted_private_key.encode())
            private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
            return local_instance, private_key
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to load local identity: {e}"))
            return None, None

    def _get_auth_headers(self, local_instance, private_key):
        """Generates authentication headers for an API request."""
        timestamp = datetime.now(timezone.utc).isoformat()
        hasher = hashlib.sha256(timestamp.encode('utf-8'))
        digest = hasher.digest()
        signature = private_key.sign(
            digest, rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH), hashes.SHA256()
        )
        return {
            'X-Pubkey': base64.b64encode(local_instance.pubkey.encode('utf-8')).decode('utf-8'),
            'X-Timestamp': timestamp,
            'X-Signature': base64.b64encode(signature).decode('utf-8')
        }

    def handle(self, *args, **options):
        peer_url = options['peer_onion_url']
        self.stdout.write(self.style.SUCCESS(f"--- Comparing sync status with peer: {peer_url} ---"))

        local_instance, private_key = self._load_identity()
        if not private_key:
            return

        # 1. Get all manifests from the remote peer
        self.stdout.write("\n[1] Fetching all manifests from remote peer...")
        
        since_param = datetime.min.replace(tzinfo=timezone.utc).isoformat()
        target_url = f"{peer_url.strip('/')}/api/sync/?since={since_param}"
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        
        try:
            headers = self._get_auth_headers(local_instance, private_key)
            response = requests.get(target_url, headers=headers, proxies=proxies, timeout=120)
            
            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"Error fetching data from peer. Status: {response.status_code}, Body: {response.text}"))
                return
            
            remote_manifests = response.json().get('manifests', [])
            remote_hashes = {m['content_hash'] for m in remote_manifests}
            self.stdout.write(f"  - Peer advertised {len(remote_hashes)} unique content items.")
        
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Network error while contacting peer: {e}"))
            return
        
        # 2. Get all content hashes stored locally
        self.stdout.write("\n[2] Checking for content stored locally...")
        local_message_hashes = set(Message.objects.values_list('manifest__content_hash', flat=True))
        local_file_hashes = set(FileAttachment.objects.values_list('manifest__content_hash', flat=True))
        local_hashes = local_message_hashes.union(local_file_hashes)
        self.stdout.write(f"  - Found {len(local_hashes)} unique content items in the local database.")
        
        # 3. Compare the two sets
        self.stdout.write("\n[3] Comparing remote manifests to local database...")
        missing_hashes = remote_hashes - local_hashes
        
        if not missing_hashes:
            self.stdout.write(self.style.SUCCESS("  - Everything is in sync! No missing content found."))
        else:
            self.stdout.write(self.style.WARNING(f"  - Found {len(missing_hashes)} item(s) that are on the peer but NOT in the local database:"))
            for h in missing_hashes:
                # Find the full manifest for the missing hash to provide more detail
                missing_manifest = next((m for m in remote_manifests if m['content_hash'] == h), None)
                if missing_manifest:
                    content_type = missing_manifest.get('content_type', 'unknown')
                    filename = missing_manifest.get('filename', 'N/A')
                    self.stdout.write(f"    - Type: {content_type}, Hash: {h[:16]}..., Filename: {filename}")

        self.stdout.write("\n--- Comparison Complete ---")
