# core/management/commands/test_db_write.py
from django.core.management.base import BaseCommand
from core.models import TrustedInstance

class Command(BaseCommand):
    help = "Tests writing to the database."

    def handle(self, *args, **options):
        try:
            instance = TrustedInstance.objects.create(web_ui_onion_url="test")
            self.stdout.write(self.style.SUCCESS("Successfully wrote to the database."))
            instance.delete()
            self.stdout.write(self.style.SUCCESS("Successfully deleted from the database."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to write to the database: {e}"))
