# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7

from django.core.management.base import BaseCommand
from applets.models import Applet, AppletData, AppletSharedState, HighScore, AppletCategory
from messaging.models import MessageBoard
from core.models import User
from pathlib import Path
import json
import shutil
import logging
from datetime import datetime
from django.utils import timezone as django_timezone
import uuid

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Restore applets from a backup directory'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_dir',
            type=str,
            help='Path to the backup directory to restore from'
        )
        parser.add_argument(
            '--applet',
            type=str,
            help='Name of specific applet to restore (optional, restores all if not specified)'
        )
        parser.add_argument(
            '--skip-chunks',
            action='store_true',
            help='Skip restoring chunks (useful if chunks will be downloaded from peer)'
        )
        parser.add_argument(
            '--rekey',
            action='store_true',
            help='Re-key manifests for current trusted instances after restore'
        )

    def handle(self, *args, **options):
        backup_dir = Path(options['backup_dir'])
        applet_name = options.get('applet')
        skip_chunks = options['skip_chunks']
        rekey = options['rekey']

        if not backup_dir.exists():
            self.stdout.write(self.style.ERROR(f'Backup directory not found: {backup_dir}'))
            return

        # Read backup manifest
        manifest_path = backup_dir / 'backup_manifest.json'
        if not manifest_path.exists():
            self.stdout.write(self.style.ERROR(f'Backup manifest not found: {manifest_path}'))
            return

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        self.stdout.write(f'Restoring from backup: {manifest["backup_date"]}\n')

        total_applets = 0
        total_chunks = 0
        total_data = 0
        total_scores = 0
        skipped_applets = 0

        # Get list of applets to restore
        if applet_name:
            applet_dirs = [d for d in backup_dir.iterdir() if d.is_dir() and d.name != '__pycache__']
            applet_dirs = [d for d in applet_dirs if d.name.replace('_', ' ') == applet_name or d.name == applet_name]
            if not applet_dirs:
                self.stdout.write(self.style.ERROR(f'Applet "{applet_name}" not found in backup'))
                return
        else:
            applet_dirs = [d for d in backup_dir.iterdir() if d.is_dir() and d.name != '__pycache__']

        for applet_dir in applet_dirs:
            metadata_path = applet_dir / 'metadata.json'
            if not metadata_path.exists():
                continue

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            applet_name = metadata['name']
            self.stdout.write(f'Restoring applet: {applet_name}')

            # Check if applet already exists
            existing_applet = Applet.objects.filter(name=applet_name).first()
            if existing_applet:
                self.stdout.write(f'  ⚠ Applet "{applet_name}" already exists, skipping')
                skipped_applets += 1
                continue

            # Get or create category
            category = None
            if metadata.get('category'):
                category, _ = AppletCategory.objects.get_or_create(name=metadata['category'])

            # Get or create event board
            event_board = None
            if metadata.get('event_board'):
                event_board, _ = MessageBoard.objects.get_or_create(name=metadata['event_board'])

            # Find owner by pubkey (if exists)
            owner = None
            if metadata.get('author_pubkey'):
                owner = User.objects.filter(pubkey=metadata['author_pubkey']).first()

            # Create applet
            applet = Applet.objects.create(
                id=uuid.UUID(metadata['id']),
                name=metadata['name'],
                description=metadata['description'],
                author_pubkey=metadata['author_pubkey'],
                code_manifest=metadata['code_manifest'],
                parameters=metadata['parameters'],
                is_local=metadata['is_local'],
                created_at=django_timezone.datetime.fromisoformat(metadata['created_at']),
                category=category,
                is_debug_mode=metadata['is_debug_mode'],
                event_board=event_board,
                handles_mime_types=metadata['handles_mime_types'],
                owner=owner,
            )

            # Restore chunks
            chunks_restored = 0
            if not skip_chunks and applet.code_manifest:
                content_hash = applet.code_manifest.get('content_hash')
                if content_hash:
                    source_chunk_dir = applet_dir / 'chunks'
                    if source_chunk_dir.exists():
                        dest_chunk_dir = Path('data/bitsync_chunks') / content_hash
                        dest_chunk_dir.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(source_chunk_dir, dest_chunk_dir, dirs_exist_ok=True)
                        chunks_restored = len(list(source_chunk_dir.glob('*.chunk')))
                        total_chunks += chunks_restored

            # Restore AppletData instances
            data_restored = 0
            data_path = applet_dir / 'applet_data.json'
            if data_path.exists():
                with open(data_path, 'r') as f:
                    data_list = json.load(f)

                for data_item in data_list:
                    # Find owner by pubkey
                    owner = User.objects.filter(pubkey=data_item['owner_pubkey']).first()
                    if not owner:
                        self.stdout.write(f'    ⚠ Owner not found for data instance, skipping')
                        continue

                    # Create AppletData
                    applet_data = AppletData.objects.create(
                        id=uuid.UUID(data_item['id']),
                        applet=applet,
                        owner=owner,
                        data_manifest=data_item['data_manifest'],
                        last_updated=django_timezone.datetime.fromisoformat(data_item['last_updated']),
                    )

                    # Restore data chunks
                    if not skip_chunks and data_item['data_manifest']:
                        data_hash = data_item['data_manifest'].get('content_hash')
                        if data_hash:
                            source_data_dir = applet_dir / 'data_chunks' / data_item['owner_username']
                            if source_data_dir.exists():
                                dest_data_dir = Path('data/bitsync_chunks') / data_hash
                                dest_data_dir.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copytree(source_data_dir, dest_data_dir, dirs_exist_ok=True)

                    data_restored += 1

                total_data += data_restored

            # Restore HighScores
            scores_restored = 0
            scores_path = applet_dir / 'high_scores.json'
            if scores_path.exists():
                with open(scores_path, 'r') as f:
                    scores_list = json.load(f)

                for score_item in scores_list:
                    HighScore.objects.create(
                        applet=applet,
                        owner_pubkey=score_item['owner_pubkey'],
                        owner_nickname=score_item['owner_nickname'],
                        score=score_item['score'],
                        wins=score_item.get('wins'),
                        losses=score_item.get('losses'),
                        kills=score_item.get('kills'),
                        deaths=score_item.get('deaths'),
                        assists=score_item.get('assists'),
                        last_updated=django_timezone.datetime.fromisoformat(score_item['last_updated']),
                    )
                    scores_restored += 1

                total_scores += scores_restored

            # Restore SharedState
            state_path = applet_dir / 'shared_state.json'
            if state_path.exists():
                with open(state_path, 'r') as f:
                    state_data = json.load(f)

                AppletSharedState.objects.create(
                    applet=applet,
                    state_data=state_data['state_data'],
                    version=state_data['version'],
                    last_updated=django_timezone.datetime.fromisoformat(state_data['last_updated']),
                )

            total_applets += 1
            self.stdout.write(f'  ✓ {applet_name}: {chunks_restored} chunks, {data_restored} data instances, {scores_restored} scores')

        # Re-key manifests if requested
        if rekey and total_applets > 0:
            self.stdout.write('\nRe-keying manifests for current trusted instances...')
            from core.services.bitsync_service import BitSyncService
            bitsync_service = BitSyncService()

            rekeyed = 0
            for applet in Applet.objects.filter(name__in=[metadata['name'] for metadata in [
                json.load(open(d / 'metadata.json')) for d in applet_dirs if (d / 'metadata.json').exists()
            ]]):
                try:
                    updated_manifest = bitsync_service.rekey_manifest_for_new_peers(applet.code_manifest)
                    applet.code_manifest = updated_manifest
                    applet.save()
                    rekeyed += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Failed to rekey {applet.name}: {e}'))

            self.stdout.write(f'  ✓ Re-keyed {rekeyed} applet manifests')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Restore complete!\n'
            f'  Applets restored: {total_applets}\n'
            f'  Applets skipped: {skipped_applets}\n'
            f'  Chunks restored: {total_chunks}\n'
            f'  Data instances: {total_data}\n'
            f'  High scores: {total_scores}'
        ))

        if skip_chunks and total_applets > 0:
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Chunks were not restored. Run the following command to download them:\n'
                f'  python manage.py download_applet_chunks'
            ))
