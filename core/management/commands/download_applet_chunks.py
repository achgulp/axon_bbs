# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7

from django.core.management.base import BaseCommand
from applets.models import Applet
from core.services.sync_service import SyncService
from core.services.bitsync_service import BitSyncService
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Download missing chunks for applets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--applet',
            type=str,
            help='Name of specific applet to download (optional, downloads all if not specified)'
        )

    def handle(self, *args, **options):
        # Initialize services and service_manager
        from core.services.service_manager import service_manager

        bitsync_service = BitSyncService()
        service_manager.bitsync_service = bitsync_service

        sync_service = SyncService()
        sync_service._load_identity()
        service_manager.sync_service = sync_service

        if not sync_service.private_key:
            self.stdout.write(self.style.ERROR('Sync service not initialized. Cannot download content.'))
            return

        # Get applets to download
        applet_name = options.get('applet')
        if applet_name:
            applets = Applet.objects.filter(name=applet_name)
            if not applets.exists():
                self.stdout.write(self.style.ERROR(f'Applet "{applet_name}" not found'))
                return
        else:
            applets = Applet.objects.filter(code_manifest__isnull=False)

        self.stdout.write(f'Checking {applets.count()} applet(s) for missing chunks...\n')

        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        for applet in applets:
            manifest = applet.code_manifest
            content_hash = manifest.get('content_hash')
            chunk_hashes = manifest.get('chunk_hashes', [])

            # Check if chunks are missing
            if bitsync_service.are_all_chunks_local(manifest):
                self.stdout.write(f'  {applet.name}: All chunks present, skipping')
                total_skipped += 1
                continue

            self.stdout.write(f'  {applet.name}: Downloading {len(chunk_hashes)} chunks...')

            try:
                # Download all chunks using sync service
                encrypted_data = sync_service._download_content(manifest)

                if encrypted_data:
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Downloaded successfully'))
                    total_downloaded += 1
                else:
                    self.stdout.write(self.style.ERROR(f'    ✗ Download failed'))
                    total_failed += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ✗ Error: {e}'))
                total_failed += 1
                import traceback
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS(
            f'\nCompleted! Downloaded: {total_downloaded}, Skipped: {total_skipped}, Failed: {total_failed}'
        ))
