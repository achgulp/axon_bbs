# axon_bbs/core/management/commands/diagnose_sync_content.py
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/management/commands/diagnose_sync_content.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import FileAttachment
from messaging.models import Message, PrivateMessage

class Command(BaseCommand):
    help = 'Scans all content and diagnoses issues that would prevent them from syncing.'
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Running Axon BBS Content Diagnostics ---"))
        now = timezone.now()
        
        # --- Check File Attachments ---
        self.stdout.write("\n[1] Checking File Attachments...")
        all_files = FileAttachment.objects.all()
        problem_files = 0
        
        if not all_files.exists():
            self.stdout.write("No file attachments found in the database.")
        else:
            for attachment in all_files:
                errors = []
                # Check 1: Manifest must exist and have a content_hash
                if not attachment.metadata_manifest or not attachment.metadata_manifest.get('content_hash'):
                    errors.append("Manifest data is missing or invalid.")
                
                # Check 2: Timestamp must not be in the future
                if attachment.created_at > now:
                    errors.append(f"Timestamp is in the future: {attachment.created_at.isoformat()}")

                if errors:
                    problem_files += 1
                    self.stdout.write(self.style.ERROR(f"  - File '{attachment.filename}' (ID: {attachment.id}) has problems:"))
                    for error in errors:
                        self.stdout.write(f"    - {error}")
            
            if problem_files == 0:
                self.stdout.write(self.style.SUCCESS(f"  OK: All {all_files.count()} file attachments appear to be syncable."))
            else:
                self.stdout.write(self.style.WARNING(f"  Found issues with {problem_files} out of {all_files.count()} file attachments."))


        # --- Check Messages ---
        self.stdout.write("\n[2] Checking Messages...")
        all_messages = Message.objects.all()
        problem_messages = 0

        if not all_messages.exists():
            self.stdout.write("No messages found in the database.")
        else:
            for message in all_messages:
                errors = []
                # Check 1: Manifest must exist and have a content_hash
                if not message.metadata_manifest or not message.metadata_manifest.get('content_hash'):
                    errors.append("Manifest data is missing or invalid.")
                
                # Check 2: Timestamp must not be in the future
                if message.created_at > now:
                    errors.append(f"Timestamp is in the future: {message.created_at.isoformat()}")

                if errors:
                    problem_messages += 1
                    self.stdout.write(self.style.ERROR(f"  - Message '{message.subject}' (ID: {message.id}) has problems:"))
                    for error in errors:
                        self.stdout.write(f"    - {error}")

            if problem_messages == 0:
                self.stdout.write(self.style.SUCCESS(f"  OK: All {all_messages.count()} messages appear to be syncable."))
            else:
                self.stdout.write(self.style.WARNING(f"  Found issues with {problem_messages} out of {all_messages.count()} messages."))

        # --- Check Private Messages ---
        self.stdout.write("\n[3] Checking Private Messages...")
        all_pms = PrivateMessage.objects.all()
        problem_pms = 0
        
        if not all_pms.exists():
            self.stdout.write("No private messages found in the database.")
        else:
            for pm in all_pms:
                errors = []
                # Check 1: Metadata manifest must exist and have a content_hash
                if not pm.metadata_manifest or not pm.metadata_manifest.get('content_hash'):
                    errors.append("Metadata manifest is missing or invalid.")
                
                # Check 2: E2E content hash must exist in metadata manifest
                if not pm.metadata_manifest.get('e2e_content_hash'):
                    errors.append("E2E content hash is missing from metadata manifest.")

                # Check 3: Timestamp must not be in the future
                if pm.created_at > now:
                    errors.append(f"Timestamp is in the future: {pm.created_at.isoformat()}")
                
                # Check 4: The e2e_encrypted_content field must exist
                if not pm.e2e_encrypted_content:
                    errors.append("E2E encrypted content is missing.")

                if errors:
                    problem_pms += 1
                    self.stdout.write(self.style.ERROR(f"  - Private Message (ID: {pm.id}) has problems:"))
                    for error in errors:
                        self.stdout.write(f"    - {error}")
            
            if problem_pms == 0:
                self.stdout.write(self.style.SUCCESS(f"  OK: All {all_pms.count()} private messages appear to be syncable."))
            else:
                self.stdout.write(self.style.WARNING(f"  Found issues with {problem_pms} out of {all_pms.count()} private messages."))

        self.stdout.write("\n--- Diagnostics Complete ---")
