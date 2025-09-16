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

# Full path: axon_bbs/core/management/commands/backfill_avatars.py
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import User
from core.services.avatar_generator import generate_cow_avatar

class Command(BaseCommand):
    help = 'Scans for active users who have a public key but no avatar and generates a unique avatar for them.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Starting Avatar Backfill Process ---"))

        # Find all active, non-agent users who have a non-empty pubkey and an empty avatar field
        users_to_update = User.objects.filter(
            Q(avatar__isnull=True) | Q(avatar=''),
            pubkey__isnull=False,
            is_active=True,
            is_agent=False
        ).exclude(pubkey__exact='')

        count = users_to_update.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("All users with public keys already have an avatar. No action needed."))
            return

        self.stdout.write(f"Found {count} user(s) needing a default avatar.")
        
        processed_count = 0
        for user in users_to_update:
            self.stdout.write(f" - Processing user: {user.username}...")
            try:
                # Generate a unique, deterministic avatar from their public key
                avatar_content_file, avatar_filename = generate_cow_avatar(user.pubkey)
                
                # Save the new avatar to the user's profile
                user.avatar.save(avatar_filename, avatar_content_file, save=True)
                
                self.stdout.write(self.style.SUCCESS(f"   Successfully generated and saved avatar for {user.username}."))
                processed_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"   Failed to generate avatar for {user.username}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n--- Avatar Backfill Complete ---"))
        self.stdout.write(f"Successfully processed {processed_count} of {count} users.")
