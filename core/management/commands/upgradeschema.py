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
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/management/commands/upgradeschema.py
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from messaging.models import PrivateMessage

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

            # --- Rebuild core_privatemessage table to remove old columns ---
            if 'core_privatemessage' in all_tables:
                self.stdout.write("Checking 'core_privatemessage' table for required rebuild...")
                cursor.execute("PRAGMA table_info(core_privatemessage);")
                columns_info = cursor.fetchall()
                column_names = [row[1] for row in columns_info]
                
                old_columns_exist = any(col in column_names for col in ['subject', 'body', 'recipient_pubkey', 'manifest'])

                if old_columns_exist:
                    self.stdout.write(self.style.WARNING("Old columns found. Rebuilding 'core_privatemessage' table to match current models..."))
                    
                    model = PrivateMessage
                    new_columns_with_types = []
                    final_fields = []
                    
                    # Manually build the column definitions for the new table
                    for field in model._meta.local_fields:
                        # Get the column name (e.g., 'author_id')
                        col_name = field.column
                        # Get the column type (e.g., 'integer')
                        col_type = field.db_type(connection=connection)
                        
                        col_def = f'"{col_name}" {col_type}'
                        
                        # Add constraints
                        if not field.null:
                            col_def += " NOT NULL"
                        if field.primary_key:
                            col_def += " PRIMARY KEY"
                            
                        new_columns_with_types.append(col_def)
                        final_fields.append(col_name)

                    # 1. Create a new table with the correct schema
                    create_sql = f"CREATE TABLE core_privatemessage_new ({', '.join(new_columns_with_types)});"
                    cursor.execute(create_sql)
                    self.stdout.write("  -> Created new temporary table.")

                    # 2. Copy data from the old table to the new one
                    common_columns = [col for col in final_fields if col in column_names]
                    common_columns_str = ', '.join(f'"{col}"' for col in common_columns)
                    insert_sql = f"INSERT INTO core_privatemessage_new ({common_columns_str}) SELECT {common_columns_str} FROM core_privatemessage;"
                    cursor.execute(insert_sql)
                    self.stdout.write(f"  -> Copied data for {len(common_columns)} matching columns.")

                    # 3. Drop the old table
                    cursor.execute("DROP TABLE core_privatemessage;")
                    self.stdout.write("  -> Dropped old table.")

                    # 4. Rename the new table
                    cursor.execute("ALTER TABLE core_privatemessage_new RENAME TO core_privatemessage;")
                    self.stdout.write("  -> Renamed new table. Rebuild complete.")
                else:
                    self.stdout.write(self.style.SUCCESS("  -> 'core_privatemessage' table already matches the current schema. No rebuild needed."))

        self.stdout.write(self.style.SUCCESS("\n--- Manual Schema Upgrade Complete ---"))
