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
