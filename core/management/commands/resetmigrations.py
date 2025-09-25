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


# Full path: axon_bbs/core/management/commands/resetmigrations.py
import os
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps


class Command(BaseCommand):
    help = 'Deletes all migration files for a specified app, leaving only the __init__.py file.'
    def add_arguments(self, parser):
        parser.add_argument('app_name', type=str, help='The name of the Django app whose migrations should be reset.')
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Delete migration files without asking for confirmation.',
        )

    def handle(self, *args, **options):
        app_name = options['app_name']
        no_input = options['no_input']
        
        try:
            app_config = apps.get_app_config(app_name)
        except LookupError:
            raise CommandError(f"App '{app_name}' not found.")

        migrations_dir = os.path.join(app_config.path, 'migrations')

        if not os.path.isdir(migrations_dir):
            self.stdout.write(self.style.WARNING(f"No 'migrations' directory found for app '{app_name}'. No action taken."))
            return

        if not no_input:
            self.stdout.write(self.style.WARNING(f"This will delete migration files for the app '{app_name}'. This cannot be undone."))
            confirm = input("Are you sure you want to continue? [y/N] ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return

        deleted_count = 0
        for filename in os.listdir(migrations_dir):
            # Skip the package initializer and non-python files
            if filename == '__init__.py' or not (filename.endswith('.py') or filename.endswith('.pyc')):
                continue

            file_path = os.path.join(migrations_dir, filename)
            try:
                os.remove(file_path)
                self.stdout.write(f"Deleted: {filename}")
                deleted_count += 1
            except OSError as e:
                self.stderr.write(self.style.ERROR(f"Error deleting {file_path}: {e}"))
        
        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully deleted {deleted_count} migration file(s) for app '{app_name}'."))
        else:
            self.stdout.write(self.style.SUCCESS("\nNo migration files to delete."))
