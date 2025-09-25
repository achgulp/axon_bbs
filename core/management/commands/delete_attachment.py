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


# Full path: axon_bbs/core/management/commands/delete_attachment.py
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import FileAttachment
import uuid

class Command(BaseCommand):
    help = 'Safely deletes a FileAttachment and removes its links from any Messages.'

    def add_arguments(self, parser):
        parser.add_argument('attachment_id', type=str, help='The UUID of the FileAttachment to delete.')

    @transaction.atomic
    def handle(self, *args, **options):
        attachment_id_str = options['attachment_id']

        try:
            attachment_id = uuid.UUID(attachment_id_str)
            attachment = FileAttachment.objects.get(id=attachment_id)
        except (ValueError, FileAttachment.DoesNotExist):
            raise CommandError(f"FileAttachment with ID '{attachment_id_str}' does not exist.")

        self.stdout.write(self.style.WARNING(f"--- Preparing to delete attachment: {attachment.filename} ({attachment.id}) ---"))

        # Find all messages that use this attachment
        messages_using_attachment = attachment.messages.all()

        if messages_using_attachment.exists():
            self.stdout.write(f"Found {messages_using_attachment.count()} message(s) linked to this attachment. Removing links...")
            # Manually remove the attachment from all messages that use it.
            # This clears the relationship in the join table.
            for msg in messages_using_attachment:
                msg.attachments.remove(attachment)
            self.stdout.write(" -> Links removed.")

        # Now, delete the attachment itself.
        self.stdout.write(f"Deleting FileAttachment object for '{attachment.filename}'...")
        attachment.delete()

        self.stdout.write(self.style.SUCCESS(f"\n--- Successfully deleted attachment '{attachment.filename}'. ---"))
