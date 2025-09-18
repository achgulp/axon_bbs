# axon_bbs/core/management/commands/cleanup_orphaned_files.py
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


# Full path: axon_bbs/core/management/commands/cleanup_orphaned_files.py
import os
import shutil
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.conf import settings
from core.models import FileAttachment, User

class Command(BaseCommand):
    help = 'Finds and deletes orphaned FileAttachments and their associated data chunks from disk.'
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List orphaned files without deleting them.',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Delete orphaned files without asking for confirmation.',
        )

    def handle(self, *args, **options):
        # Get a set of all file paths currently being used as user avatars.
        # The User.avatar field stores paths like 'avatars/cow_....png'.
        active_avatar_paths = set(User.objects.exclude(avatar__exact='').values_list('avatar', flat=True))

        # Find FileAttachment objects that are not linked to any Message
        attachments_without_messages = FileAttachment.objects.annotate(
            message_count=Count('messages')
        ).filter(message_count=0)

        # From that list, filter out any that are active avatars.
        orphaned_attachments = []
        for attachment in attachments_without_messages:
            # Construct the path as it would be stored in the User.avatar field.
            expected_avatar_path = os.path.join('avatars', attachment.filename)
            if expected_avatar_path not in active_avatar_paths:
                orphaned_attachments.append(attachment)
        
        count = len(orphaned_attachments)

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No orphaned files found."))
            return

        self.stdout.write(f"Found {count} orphaned file attachment(s).")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("--- DRY RUN ---"))
            for attachment in orphaned_attachments:
                self.stdout.write(f"[WOULD DELETE] DB Record: {attachment.filename} ({attachment.id})")
                content_hash = attachment.metadata_manifest.get('content_hash') if attachment.metadata_manifest else None
                if content_hash:
                    chunk_dir = os.path.join(settings.BASE_DIR, 'data', 'bitsync_chunks', content_hash)
                    if os.path.isdir(chunk_dir):
                        self.stdout.write(f"                Disk Chunks: {chunk_dir}")
                    else:
                        self.stdout.write(self.style.NOTICE(f"                 Disk Chunks: Not found at {chunk_dir}"))
            return

        if not options['no-input']:
            confirm = input(f"Are you sure you want to delete these {count} files and their data? [y/N] ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR("Cleanup cancelled by user."))
                return

        deleted_count = 0
        for attachment in orphaned_attachments:
            self.stdout.write(f"Deleting {attachment.filename}...")
            content_hash = attachment.metadata_manifest.get('content_hash') if attachment.metadata_manifest else None
            
            # 1. Delete the data chunks from the disk
            if content_hash:
                chunk_dir = os.path.join(settings.BASE_DIR, 'data', 'bitsync_chunks', content_hash)
                if os.path.isdir(chunk_dir):
                    try:
                        shutil.rmtree(chunk_dir)
                        self.stdout.write(self.style.SUCCESS(f"  - Successfully deleted chunk directory: {chunk_dir}"))
                    except OSError as e:
                        self.stdout.write(self.style.ERROR(f"  - Error deleting chunk directory {chunk_dir}: {e}"))
            
            # 2. Delete the FileAttachment object from the database
            attachment.delete()
            deleted_count += 1
            
        self.stdout.write(self.style.SUCCESS(f"\nCleanup complete. Deleted {deleted_count} orphaned
