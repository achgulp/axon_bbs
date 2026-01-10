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

import threading
from django.core.management.base import BaseCommand
from uat_runner import run_uat_suite

class Command(BaseCommand):
    help = 'Starts the full UAT test suite in a background thread.'

    def add_arguments(self, parser):
        parser.add_argument('peer_onion_url', type=str, help='The .onion URL of the peer BBS to run the verifier on.')

    def handle(self, *args, **options):
        peer_onion_url = options['peer_onion_url']
        self.stdout.write(self.style.SUCCESS(f"--- Starting UAT Suite against {peer_onion_url} in a background thread... ---"))
        
        # Run the UAT suite in a separate thread to avoid blocking the server
        uat_thread = threading.Thread(target=run_uat_suite, args=(peer_onion_url,), daemon=True)
        uat_thread.start()
        
        self.stdout.write("UAT thread started. Check the 'UAT-Channel' message board for results.")
