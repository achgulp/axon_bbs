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


# Full path: axon_bbs/core/management/commands/cleanup_test_user.py
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from messaging.models import Message, PrivateMessage
from core.models import FileAttachment
from federation.models import ModerationReport

User = get_user_model()

class Command(BaseCommand):
    help = 'Safely deletes a test user and all of their associated content.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='The username of the user to delete.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Shows what would be deleted without actually deleting anything.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options['username']
        dry_run = options['dry_run']

        try:
            user_to_delete = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        self.stdout.write(self.style.WARNING(f"--- Preparing to delete user: {username} ---"))
        if dry_run:
            self.stdout.write(self.style.NOTICE("--- DRY RUN MODE ---"))
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


# Full path: axon_bbs/core/management/commands/cleanup_test_user.py
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from messaging.models import Message, PrivateMessage
from core.models import FileAttachment
from federation.models import ModerationReport

User = get_user_model()

class Command(BaseCommand):
    help = 'Safely deletes a test user and all of their associated content.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='The username of the user to delete.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Shows what would be deleted without actually deleting anything.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options['username']
        dry_run = options['dry_run']

        try:
            user_to_delete = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        self.stdout.write(self.style.WARNING(f"--- Preparing to delete user: {username} ---"))
        if dry_run:
            self.stdout.write(self.style.NOTICE("--- DRY RUN MODE ---"))

        # 1. Messages authored by the user
        messages = Message.objects.filter(author=user_to_delete)
        if messages.exists():
            self.stdout.write(f"Found {messages.count()} public message(s) to delete.")
            if not dry_run:
                for msg in messages:
                    # Manually clear the M2M relationship first
                    msg.attachments.clear()
                messages.delete()

        # 2. Private Messages sent or received
        pms = PrivateMessage.objects.filter(Q(author=user_to_delete) | Q(recipient=user_to_delete))
        if pms.exists():
            self.stdout.write(f"Found {pms.count()} private message(s) to delete.")
            if not dry_run:
                pms.delete()
        
        # 3. File Attachments authored by the user
        attachments = FileAttachment.objects.filter(author=user_to_delete)
        if attachments.exists():
            self.stdout.write(f"Found {attachments.count()} file attachment(s) to delete.")
            if not dry_run:
                attachments.delete()

        # 4. Reports filed by the user
        reports = ModerationReport.objects.filter(reporting_user=user_to_delete)
        if reports.exists():
            self.stdout.write(f"Found {reports.count()} moderation report(s) to delete.")
            if not dry_run:
                reports.delete()

        # 5. Finally, delete the user
        self.stdout.write(f"Deleting user object for '{username}'...")
        if not dry_run:
            user_to_delete.delete()

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n--- Dry run complete. No changes were made. ---"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n--- Successfully deleted user '{username}' and all associated content. ---"))
        # 1. Messages authored by the user
        messages = Message.objects.filter(author=user_to_delete)
        if messages.exists():
            self.stdout.write(f"Found {messages.count()} public message(s) to delete.")
            if not dry_run:
                for msg in messages:
                    # Manually clear the M2M relationship first
                    msg.attachments.clear()
                messages.delete()

        # 2. Private Messages sent or received
        pms = PrivateMessage.objects.filter(Q(author=user_to_delete) | Q(recipient=user_to_delete))
        if pms.exists():
            self.stdout.write(f"Found {pms.count()} private message(s) to delete.")
            if not dry_run:
                pms.delete()
        
        # 3. File Attachments authored by the user
        attachments = FileAttachment.objects.filter(author=user_to_delete)
        if attachments.exists():
            self.stdout.write(f"Found {attachments.count()} file attachment(s) to delete.")
            if not dry_run:
                attachments.delete()

        # 4. Reports filed by the user
        reports = ModerationReport.objects.filter(reporting_user=user_to_delete)
        if reports.exists():
            self.stdout.write(f"Found {reports.count()} moderation report(s) to delete.")
            if not dry_run:
                reports.delete()

        # 5. Finally, delete the user
        self.stdout.write(f"Deleting user object for '{username}'...")
        if not dry_run:
            user_to_delete.delete()

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\n--- Dry run complete. No changes were made. ---"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n--- Successfully deleted user '{username}' and all associated content. ---"))
