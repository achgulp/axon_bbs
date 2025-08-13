# Full path: axon_bbs/core/management/commands/update_peer_key.py
import requests
from django.core.management.base import BaseCommand
from core.models import TrustedInstance

class Command(BaseCommand):
    help = 'Fetches a peer\'s public key directly from its API and updates the local record.'

    def add_arguments(self, parser):
        parser.add_argument('peer_onion_url', type=str, help="The full .onion URL of the peer to update.")

    def handle(self, *args, **options):
        peer_url = options['peer_onion_url']
        self.stdout.write(self.style.SUCCESS(f"--- Attempting to update key for peer: {peer_url} ---"))

        try:
            peer_instance = TrustedInstance.objects.get(web_ui_onion_url=peer_url)
        except TrustedInstance.DoesNotExist:
            self.stderr.write(self.style.ERROR("Peer not found in local database. Please add it first."))
            return

        target_url = f"{peer_url.strip('/')}/api/identity/public_key/"
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

        self.stdout.write("Fetching key from peer over Tor...")
        try:
            response = requests.get(target_url, proxies=proxies, timeout=120)
            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"Peer returned an error. Status: {response.status_code}, Body: {response.text}"))
                return
            
            new_key = response.json().get('public_key')
            if not new_key:
                self.stderr.write(self.style.ERROR("Peer response did not contain a public key."))
                return

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Network error while contacting peer: {e}"))
            return
            
        self.stdout.write("Successfully fetched key. Updating local database...")
        peer_instance.pubkey = new_key
        peer_instance.save()
        
        self.stdout.write(self.style.SUCCESS("Peer's public key has been updated successfully."))
