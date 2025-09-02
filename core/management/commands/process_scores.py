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


# Full path: axon_bbs/core/management/commands/process_scores.py
from django.core.management.base import BaseCommand
from core.services.high_score_service import HighScoreService

class Command(BaseCommand):
    help = 'Manually triggers the high score processing service.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("--- Manually running High Score processing... ---"))
        
        try:
            service = HighScoreService()
            service.process_scores()
            self.stdout.write(self.style.SUCCESS("--- High Score processing complete. ---"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))
