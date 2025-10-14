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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


from django.core.management.base import BaseCommand
from applets.models import Applet
from core.models import TrustedInstance
from core.services.bitsync_service import BitSyncService
import requests
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch and update applet manifests from a trusted peer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--peer',
            type=str,
            help='Onion URL of the peer to sync from (optional, uses first trusted peer if not specified)'
        )

    def handle(self, *args, **options):
        bitsync_service = BitSyncService()

        # Get peer
        peer_url = options.get('peer')
        if peer_url:
            try:
                peer = TrustedInstance.objects.get(web_ui_onion_url=peer_url, is_trusted_peer=True)
            except TrustedInstance.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Peer {peer_url} not found or not trusted'))
                return
        else:
            peer = TrustedInstance.objects.filter(is_trusted_peer=True).first()
            if not peer:
                self.stdout.write(self.style.ERROR('No trusted peers found'))
                return

        self.stdout.write(f'Syncing applets from: {peer.web_ui_onion_url}')

        # Get local instance for auth
        local_instance = TrustedInstance.objects.filter(
            encrypted_private_key__isnull=False,
            is_trusted_peer=False
        ).first()

        if not local_instance:
            self.stdout.write(self.style.ERROR('Local instance not configured'))
            return

        # Load private key for auth
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
        from django.conf import settings
        import hashlib

        try:
            key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
            f = Fernet(key)
            decrypted_pem = f.decrypt(local_instance.encrypted_private_key.encode())
            private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load private key: {e}'))
            return

        # Create auth headers
        timestamp = datetime.now(timezone.utc).isoformat()
        hasher = hashlib.sha256(timestamp.encode('utf-8'))
        digest = hasher.digest()
        signature = private_key.sign(
            digest,
            rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )

        headers = {
            'X-Pubkey': base64.b64encode(local_instance.pubkey.encode('utf-8')).decode('utf-8'),
            'X-Timestamp': timestamp,
            'X-Signature': base64.b64encode(signature).decode('utf-8')
        }

        # Request sync with very old timestamp to get ALL content
        old_timestamp = datetime(2000, 1, 1, tzinfo=timezone.utc).isoformat()
        url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={old_timestamp}"
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

        try:
            self.stdout.write('Fetching manifests from peer...')
            response = requests.get(url, headers=headers, proxies=proxies, timeout=120)

            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Peer returned status {response.status_code}'))
                return

            data = response.json()
            manifests = data.get('manifests', [])

            # Filter for applets only
            applet_manifests = [m for m in manifests if m.get('content_type') == 'applet']

            self.stdout.write(f'Received {len(applet_manifests)} applet manifest(s)')

            updated_count = 0
            failed_count = 0

            for manifest in applet_manifests:
                content_hash = manifest.get('content_hash')
                if not content_hash:
                    continue

                try:
                    # Find local applet with this content hash
                    applet = Applet.objects.filter(code_manifest__content_hash=content_hash).first()

                    if applet:
                        # Update with manifest from peer (which has been just-in-time rekeyed)
                        # Re-key for all local instances
                        updated_manifest = bitsync_service.rekey_manifest_for_new_peers(manifest)
                        applet.code_manifest = updated_manifest
                        applet.save()
                        updated_count += 1
                        self.stdout.write(f'✓ Updated applet: {applet.name}')
                    else:
                        self.stdout.write(f'  Skipping unknown applet with hash {content_hash[:10]}...')

                except Exception as e:
                    failed_count += 1
                    self.stdout.write(self.style.ERROR(f'✗ Failed to update applet: {e}'))

            self.stdout.write(self.style.SUCCESS(
                f'\nCompleted! Updated {updated_count} applets, {failed_count} failed.'
            ))

        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Network error: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            import traceback
            traceback.print_exc()
