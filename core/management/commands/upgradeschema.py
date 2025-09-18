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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/management/commands/upgradeschema.py
from django.core.management.base import BaseCommand
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'Manually upgrades the database schema to the version 10.13.0 state without using migrations.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("--- Starting Manual Schema Upgrade ---"))
        self.stdout.write(self.style.WARNING("IMPORTANT: Ensure you have backed up your database before proceeding."))
        
        confirm = input("Are you sure you want to alter the database schema directly? [y/N] ")
        if confirm.lower() != 'y':
            self.stdout.write(self.style.ERROR("Operation cancelled."))
            return

        with connection.cursor() as cursor:
            # --- Get schema information ---
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            all_tables = [row[0] for row in cursor.fetchall()]

            # --- Upgrade core_fileattachment table ---
            if 'core_fileattachment' in all_tables:
                cursor.execute("PRAGMA table_info(core_fileattachment);")
                columns = [row[1] for row in cursor.fetchall()]
                if 'manifest' in columns and 'metadata_manifest' not in columns:
                    self.stdout.write("Renaming 'manifest' to 'metadata_manifest' in 'core_fileattachment'...")
                    cursor.execute("ALTER TABLE core_fileattachment RENAME COLUMN manifest TO metadata_manifest;")
                    self.stdout.write(self.style.SUCCESS("  -> Done."))

            # --- Upgrade core_message table ---
            if 'core_message' in all_tables:
                cursor.execute("PRAGMA table_info(core_message);")
                columns = [row[1] for row in cursor.fetchall()]
                if 'manifest' in columns and 'metadata_manifest' not in columns:
                    self.stdout.write("Renaming 'manifest' to 'metadata_manifest' in 'core_message'...")
                    cursor.execute("ALTER TABLE core_message RENAME COLUMN manifest TO metadata_manifest;")
                    self.stdout.write(self.style.SUCCESS("  -> Done."))

            # --- Upgrade core_privatemessage table ---
            if 'core_privatemessage' in all_tables:
                cursor.execute("PRAGMA table_info(core_privatemessage);")
                columns = [row[1] for row in cursor.fetchall()]
                # Add new columns if they don't exist
                if 'e2e_encrypted_content' not in columns:
                    self.stdout.write("Adding 'e2e_encrypted_content' to 'core_privatemessage'...")
                    cursor.execute("ALTER TABLE core_privatemessage ADD COLUMN e2e_encrypted_content TEXT NULL;")
                    self.stdout.write(self.style.SUCCESS("  -> Done."))
                if 'metadata_manifest' not in columns:
                    self.stdout.write("Adding 'metadata_manifest' to 'core_privatemessage'...")
                    cursor.execute("ALTER TABLE core_privatemessage ADD COLUMN metadata_manifest TEXT NULL;")
                    self.stdout.write(self.style.SUCCESS("  -> Done."))

                self.stdout.write(self.style.NOTICE("NOTE: Old, unused columns may remain in the 'core_privatemessage' table. This is safe and expected as SQLite does not support dropping columns easily."))

        self.stdout.write(self.style.SUCCESS("\n--- Manual Schema Upgrade Complete ---"))

