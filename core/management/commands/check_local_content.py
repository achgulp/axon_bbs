# Full path: axon_bbs/core/management/commands/check_local_content.py
from django.core.management.base import BaseCommand
from core.models import FileAttachment, Message
from core.services.service_manager import service_manager

class Command(BaseCommand):
    help = 'Scans the local database and checks if all data chunks for each content item are present on disk.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Running Axon BBS Local Content Integrity Check ---"))
        
        if not service_manager.bitsync_service:
            self.stderr.write(self.style.ERROR("BitSyncService is not available."))
            return

        # --- Check File Attachments ---
        self.stdout.write("\n[1] Checking File Attachments...")
        all_files = FileAttachment.objects.all()
        
        if not all_files.exists():
            self.stdout.write("No file attachments found in the database.")
        else:
            incomplete_files = []
            for attachment in all_files:
                if not service_manager.bitsync_service.are_all_chunks_local(attachment.manifest):
                    incomplete_files.append(attachment)
            
            complete_count = all_files.count() - len(incomplete_files)
            self.stdout.write(self.style.SUCCESS(f"  - Found {complete_count} COMPLETE file(s)."))
            
            if incomplete_files:
                self.stdout.write(self.style.WARNING(f"  - Found {len(incomplete_files)} INCOMPLETE file(s) (missing data chunks):"))
                for attachment in incomplete_files:
                    self.stdout.write(f"    - {attachment.filename} (ID: {attachment.id})")

        # --- Check Messages ---
        self.stdout.write("\n[2] Checking Messages...")
        all_messages = Message.objects.all()

        if not all_messages.exists():
            self.stdout.write("No messages found in the database.")
        else:
            incomplete_messages = []
            for message in all_messages:
                # Messages without manifests are local-only and not syncable
                if message.manifest:
                    if not service_manager.bitsync_service.are_all_chunks_local(message.manifest):
                        incomplete_messages.append(message)
            
            complete_count = all_messages.count() - len(incomplete_messages)
            self.stdout.write(self.style.SUCCESS(f"  - Found {complete_count} COMPLETE message(s)."))

            if incomplete_messages:
                self.stdout.write(self.style.WARNING(f"  - Found {len(incomplete_messages)} INCOMPLETE message(s) (missing data chunks):"))
                for message in incomplete_messages:
                    self.stdout.write(f"    - {message.subject} (ID: {message.id})")


        self.stdout.write("\n--- Integrity Check Complete ---")
