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
from django.db.models import Q
from django.contrib.auth import get_user_model
from messaging.models import Message, PrivateMessage
from core.models import FileAttachment
from federation.models import ModerationReport, FederatedAction
from accounts.models import IgnoredPubkey
from applets.models import AppletData

User = get_user_model()

class Command(BaseCommand):
    help = 'Forcefully deletes a test user and all of their associated content in a safe order.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='The username of the user to delete.')

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        self.stdout.write(self.style.WARNING(f"--- Forcefully cleaning up user: {username} ---"))

        # Step 1: Delete reports filed BY this user
        reports_filed = ModerationReport.objects.filter(reporting_user=user)
        if reports_filed.exists():
            count = reports_filed.count()
            reports_filed.delete()
            self.stdout.write(f" -> Deleted {count} moderation report(s) filed by this user.")

        # Step 2: Delete reports filed AGAINST messages authored by this user
        messages_by_user = Message.objects.filter(author=user)
        reports_against = ModerationReport.objects.filter(reported_message__in=messages_by_user)
        if reports_against.exists():
            count = reports_against.count()
            reports_against.delete()
            self.stdout.write(f" -> Deleted {count} moderation report(s) filed against this user's messages.")

        # Step 3: Manually clear M2M attachments from messages, then delete messages
        if messages_by_user.exists():
            count = messages_by_user.count()
            for msg in messages_by_user:
                msg.attachments.clear()
            messages_by_user.delete()
            self.stdout.write(f" -> Cleared attachments and deleted {count} public message(s).")

        # Step 4: Delete Private Messages
        pms = PrivateMessage.objects.filter(Q(author=user) | Q(recipient=user))
        if pms.exists():
            count = pms.count()
            pms.delete()
            self.stdout.write(f" -> Deleted {count} private message(s).")

        # Step 5: Delete File Attachments
        attachments = FileAttachment.objects.filter(author=user)
        if attachments.exists():
            count = attachments.count()
            attachments.delete()
            self.stdout.write(f" -> Deleted {count} file attachment(s).")

        # Step 6: Delete other simple related objects
        related_models = [IgnoredPubkey, AppletData, FederatedAction]
        for model in related_models:
            # Find the field that links to the User model
            user_field_name = None
            for field in model._meta.get_fields():
                if field.related_model == User:
                    user_field_name = field.name
                    break

            if user_field_name:
                qs = model.objects.filter(**{user_field_name: user})
                if qs.exists():
                    count = qs.count()
                    qs.delete()
                    self.stdout.write(f" -> Deleted {count} object(s) from {model.__name__}.")

        # Step 7: Delete the user
        self.stdout.write(f" -> Deleting final user object for '{username}'...")
        user.delete()

        self.stdout.write(self.style.SUCCESS(f"\n--- Successfully force-deleted user '{username}'. ---"))
