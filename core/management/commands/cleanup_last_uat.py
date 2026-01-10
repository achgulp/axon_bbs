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


# Full path: axon_bbs/core/management/commands/cleanup_last_uat.py
import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from messaging.models import Message, MessageBoard

class Command(BaseCommand):
    help = 'Reads the last UAT log from the UAT-Channel and deletes all users created during that run.'

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Automated UAT Cleanup ---")
        
        try:
            uat_board = MessageBoard.objects.get(name="UAT-Channel")
            log_message = Message.objects.filter(
                board=uat_board,
                subject__startswith="UAT_CLEANUP_LOG_"
            ).latest('created_at')
        except MessageBoard.DoesNotExist:
            raise CommandError("UAT-Channel message board not found.")
        except Message.DoesNotExist:
            raise CommandError("No UAT cleanup log message found in the UAT-Channel.")

        self.stdout.write(f"Found UAT log message: '{log_message.subject}'")
        
        pubkeys_to_delete = set()
        try:
            log_data = json.loads(log_message.body)
            
            # Find the pubkey for the first user
            profile_step = next((item for item in log_data if item['step'].startswith("3)")), None)
            if profile_step and profile_step['status'] == 'PASS' and profile_step['details'].get('pubkey'):
                pubkey = profile_step['details']['pubkey']
                pubkeys_to_delete.add(pubkey)
                self.stdout.write(f" -> Found pubkey for first UAT user: {pubkey[:20]}...")
            
            # Find the pubkey for the second user
            from core.models import User
            user2_step = next((item for item in log_data if item['step'].startswith("7a)")), None)
            if user2_step and user2_step['status'] == 'PASS':
                # MODIFIED: Read the nickname from the details dictionary
                nickname = user2_step['details'].get('nickname')
                if nickname:
                    try:
                        user2 = User.objects.get(nickname=nickname)
                        if user2.pubkey:
                            pubkeys_to_delete.add(user2.pubkey)
                            self.stdout.write(f" -> Found pubkey for second UAT user: {user2.pubkey[:20]}...")
                    except User.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f" -> Could not find second UAT user with nickname {nickname}."))
                else:
                    self.stdout.write(self.style.WARNING(" -> Log entry for second user was missing details."))


        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise CommandError(f"Could not parse UAT log message body. Error: {e}")

        if not pubkeys_to_delete:
            self.stdout.write(self.style.WARNING("Could not find any public keys in the log to clean up."))
            return

        self.stdout.write(self.style.NOTICE("\nCalling the 'cleanup_test_user' command for each found public key..."))

        for pubkey in pubkeys_to_delete:
            try:
                call_command('cleanup_test_user', pubkey=pubkey)
            except CommandError as e:
                self.stdout.write(self.style.WARNING(f"Could not clean up user with pubkey {pubkey[:20]}... They may have already been deleted. Error: {e}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An unexpected error occurred while cleaning up pubkey {pubkey[:20]}...: {e}"))
        
        self.stdout.write(self.style.SUCCESS("\n--- Automated UAT cleanup complete. ---"))
