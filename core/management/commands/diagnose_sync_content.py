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


# Full path: axon_bbs/core/management/commands/diagnose_sync_content.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import FileAttachment, Message

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
                if not attachment.manifest or not attachment.manifest.get('content_hash'):
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
                if not message.manifest or not message.manifest.get('content_hash'):
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

        self.stdout.write("\n--- Diagnostics Complete ---")
