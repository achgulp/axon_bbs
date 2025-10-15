# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7

from django.core.management.base import BaseCommand
from applets.models import Applet, AppletData, AppletSharedState, HighScore
from pathlib import Path
import json
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backup all applets (metadata, chunks, and data) to a backup directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='applet_backups',
            help='Directory to store backups (default: applet_backups)'
        )
        parser.add_argument(
            '--applet',
            type=str,
            help='Name of specific applet to backup (optional, backs up all if not specified)'
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output'])
        applet_name = options.get('applet')

        # Create timestamped backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = output_dir / f'backup_{timestamp}'
        backup_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f'Creating backup in: {backup_dir}\n')

        # Get applets to backup
        if applet_name:
            applets = Applet.objects.filter(name=applet_name)
            if not applets.exists():
                self.stdout.write(self.style.ERROR(f'Applet "{applet_name}" not found'))
                return
        else:
            applets = Applet.objects.all()

        total_applets = 0
        total_chunks = 0
        total_data = 0
        total_scores = 0

        for applet in applets:
            self.stdout.write(f'Backing up applet: {applet.name}')

            # Create applet directory
            applet_dir = backup_dir / applet.name.replace('/', '_').replace(' ', '_')
            applet_dir.mkdir(exist_ok=True)

            # 1. Save applet metadata
            metadata = {
                'id': str(applet.id),
                'name': applet.name,
                'description': applet.description,
                'author_pubkey': applet.author_pubkey,
                'code_manifest': applet.code_manifest,
                'parameters': applet.parameters,
                'is_local': applet.is_local,
                'created_at': applet.created_at.isoformat(),
                'category': applet.category.name if applet.category else None,
                'is_debug_mode': applet.is_debug_mode,
                'event_board': applet.event_board.name if applet.event_board else None,
                'handles_mime_types': applet.handles_mime_types,
            }

            with open(applet_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            # 2. Backup chunks
            chunks_backed_up = 0
            if applet.code_manifest:
                content_hash = applet.code_manifest.get('content_hash')
                if content_hash:
                    source_chunk_dir = Path('data/bitsync_chunks') / content_hash
                    if source_chunk_dir.exists():
                        dest_chunk_dir = applet_dir / 'chunks'
                        shutil.copytree(source_chunk_dir, dest_chunk_dir, dirs_exist_ok=True)
                        chunks_backed_up = len(list(dest_chunk_dir.glob('*.chunk')))
                        total_chunks += chunks_backed_up

            # 3. Backup AppletData instances
            applet_data_instances = AppletData.objects.filter(applet=applet)
            data_backed_up = 0
            if applet_data_instances.exists():
                data_list = []
                for data_instance in applet_data_instances:
                    data_list.append({
                        'id': str(data_instance.id),
                        'owner_username': data_instance.owner.username,
                        'owner_pubkey': data_instance.owner.pubkey,
                        'data_manifest': data_instance.data_manifest,
                        'last_updated': data_instance.last_updated.isoformat(),
                    })

                    # Backup data chunks too
                    if data_instance.data_manifest:
                        data_hash = data_instance.data_manifest.get('content_hash')
                        if data_hash:
                            data_chunk_dir = Path('data/bitsync_chunks') / data_hash
                            if data_chunk_dir.exists():
                                dest_data_dir = applet_dir / 'data_chunks' / data_instance.owner.username
                                shutil.copytree(data_chunk_dir, dest_data_dir, dirs_exist_ok=True)

                with open(applet_dir / 'applet_data.json', 'w') as f:
                    json.dump(data_list, f, indent=2)
                data_backed_up = len(data_list)
                total_data += data_backed_up

            # 4. Backup HighScores
            high_scores = HighScore.objects.filter(applet=applet)
            scores_backed_up = 0
            if high_scores.exists():
                scores_list = []
                for score in high_scores:
                    scores_list.append({
                        'owner_pubkey': score.owner_pubkey,
                        'owner_nickname': score.owner_nickname,
                        'score': score.score,
                        'wins': score.wins,
                        'losses': score.losses,
                        'kills': score.kills,
                        'deaths': score.deaths,
                        'assists': score.assists,
                        'last_updated': score.last_updated.isoformat(),
                    })

                with open(applet_dir / 'high_scores.json', 'w') as f:
                    json.dump(scores_list, f, indent=2)
                scores_backed_up = len(scores_list)
                total_scores += scores_backed_up

            # 5. Backup SharedState
            try:
                shared_state = AppletSharedState.objects.get(applet=applet)
                state_data = {
                    'state_data': shared_state.state_data,
                    'version': shared_state.version,
                    'last_updated': shared_state.last_updated.isoformat(),
                }
                with open(applet_dir / 'shared_state.json', 'w') as f:
                    json.dump(state_data, f, indent=2)
            except AppletSharedState.DoesNotExist:
                pass

            total_applets += 1
            self.stdout.write(f'  ✓ {applet.name}: {chunks_backed_up} chunks, {data_backed_up} data instances, {scores_backed_up} scores')

        # Create backup manifest
        manifest = {
            'backup_date': timestamp,
            'total_applets': total_applets,
            'total_chunks': total_chunks,
            'total_data_instances': total_data,
            'total_high_scores': total_scores,
            'applets': [a.name for a in applets],
        }

        with open(backup_dir / 'backup_manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Backup complete!\n'
            f'  Location: {backup_dir}\n'
            f'  Applets: {total_applets}\n'
            f'  Chunks: {total_chunks}\n'
            f'  Data instances: {total_data}\n'
            f'  High scores: {total_scores}'
        ))
