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


# Full path: axon_bbs/core/management/commands/check_local_content.py
from django.core.management.base import BaseCommand
from core.models import FileAttachment
from messaging.models import Message
from core.services.service_manager import service_manager
from core.services.sync_service import SyncService

class Command(BaseCommand):
    help = 'Scans local content for missing data chunks and optionally triggers a re-download.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repair',
            action='store_true',
            help='Attempt to download missing chunks for all incomplete content.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Running Axon BBS Local Content Integrity Check ---"))
        
        if not service_manager.bitsync_service:
            self.stderr.write(self.style.ERROR("BitSyncService is not available."))
            return

        # --- Gather Incomplete Items ---
        all_files = FileAttachment.objects.all()
        incomplete_files = []
        for attachment in all_files:
            if not service_manager.bitsync_service.are_all_chunks_local(attachment.manifest):
                incomplete_files.append(attachment)
        
        all_messages = Message.objects.all()
        incomplete_messages = []
        for message in all_messages:
            if message.manifest and not service_manager.bitsync_service.are_all_chunks_local(message.manifest):
                incomplete_messages.append(message)

        # --- Print Report ---
        self.stdout.write("\n[1] Checking File Attachments...")
        self.stdout.write(self.style.SUCCESS(f"  - Found {all_files.count() - len(incomplete_files)} COMPLETE file(s)."))
        if incomplete_files:
            self.stdout.write(self.style.WARNING(f"  - Found {len(incomplete_files)} INCOMPLETE file(s) (missing data chunks):"))
            for attachment in incomplete_files:
                self.stdout.write(f"    - {attachment.filename} (ID: {attachment.id})")

        self.stdout.write("\n[2] Checking Messages...")
        self.stdout.write(self.style.SUCCESS(f"  - Found {all_messages.count() - len(incomplete_messages)} COMPLETE message(s)."))
        if incomplete_messages:
            self.stdout.write(self.style.WARNING(f"  - Found {len(incomplete_messages)} INCOMPLETE message(s) (missing data chunks):"))
            for message in incomplete_messages:
                self.stdout.write(f"    - '{message.subject}' (ID: {message.id})")

        # --- Perform Repair if Flagged ---
        if options['repair']:
            self.stdout.write(self.style.SUCCESS("\n--- Starting Repair Process ---"))
            
            # We need an instance of the SyncService to use its download methods
            sync_service = SyncService()
            sync_service._load_identity() # Load keys needed for authentication

            if not sync_service.private_key:
                self.stderr.write(self.style.ERROR("Could not load local identity. Aborting repair."))
                return

            all_incomplete_items = incomplete_files + incomplete_messages
            if not all_incomplete_items:
                self.stdout.write("No incomplete items to repair.")
            else:
                for item in all_incomplete_items:
                    item_name = getattr(item, 'filename', getattr(item, 'subject', item.id))
                    self.stdout.write(f"\nAttempting to repair '{item_name}'...")
                    sync_service._download_content(item.manifest)

            self.stdout.write(self.style.SUCCESS("\n--- Repair Process Complete ---"))
        else:
            self.stdout.write("\n--- Integrity Check Complete ---")
            if incomplete_files or incomplete_messages:
                self.stdout.write(self.style.NOTICE("Run this command with the --repair flag to download missing content."))
