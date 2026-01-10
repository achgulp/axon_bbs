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
from core.services.bitsync_service import BitSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update all applet manifests to include encryption keys for current trusted instances'

    def handle(self, *args, **options):
        # Initialize BitSync service directly
        bitsync_service = BitSyncService()

        applets = Applet.objects.filter(code_manifest__isnull=False)
        updated_count = 0
        failed_count = 0

        for applet in applets:
            try:
                updated_manifest = bitsync_service.rekey_manifest_for_new_peers(
                    applet.code_manifest
                )
                applet.code_manifest = updated_manifest
                applet.save()
                updated_count += 1
                self.stdout.write(f"Updated applet: {applet.name}")
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"Failed to update applet {applet.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted! Updated {updated_count} applets, {failed_count} failed."
        ))
