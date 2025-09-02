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


# Full path: axon_bbs/core/management/commands/reset_peer_sync_time.py
from django.core.management.base import BaseCommand
from core.models import TrustedInstance

class Command(BaseCommand):
    help = 'Finds a trusted peer by its onion URL and resets its "last_synced_at" timestamp to None.'

    def add_arguments(self, parser):
        parser.add_argument('peer_onion_url', type=str, help="The full .onion URL of the peer to reset.")

    def handle(self, *args, **options):
        peer_url = options['peer_onion_url']
        self.stdout.write(self.style.SUCCESS(f"--- Attempting to reset sync time for peer: {peer_url} ---"))

        try:
            peer = TrustedInstance.objects.get(web_ui_onion_url=peer_url)
        except TrustedInstance.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Error: Could not find a trusted peer with that URL."))
            return
        except TrustedInstance.MultipleObjectsReturned:
            self.stderr.write(self.style.ERROR(f"Error: Found multiple peers with that URL. Please clean up your database."))
            return

        self.stdout.write(f"Found peer. Current 'last_synced_at' value: {peer.last_synced_at}")

        peer.last_synced_at = None
        peer.save()

        # Re-fetch from DB to confirm the change
        peer.refresh_from_db()
        self.stdout.write(f"New 'last_synced_at' value: {peer.last_synced_at}")
        
        self.stdout.write(self.style.SUCCESS("\nTimestamp successfully cleared."))
        self.stdout.write("The next sync cycle (within 2 minutes) will perform a full sync with this peer.")
