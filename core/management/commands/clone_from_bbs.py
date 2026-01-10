# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7

from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import TrustedInstance
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clone configuration and applets from another BBS instance'

    def add_arguments(self, parser):
        parser.add_argument(
            'peer_url',
            type=str,
            help='Onion URL of the peer BBS to clone from'
        )
        parser.add_argument(
            '--backup-dir',
            type=str,
            help='Optional: Path to local backup directory to restore applets from (skips network sync)'
        )
        parser.add_argument(
            '--skip-config',
            action='store_true',
            help='Skip cloning configuration (only clone applets)'
        )
        parser.add_argument(
            '--skip-applets',
            action='store_true',
            help='Skip cloning applets (only clone configuration)'
        )

    def handle(self, *args, **options):
        peer_url = options['peer_url']
        backup_dir = options.get('backup_dir')
        skip_config = options['skip_config']
        skip_applets = options['skip_applets']

        self.stdout.write(self.style.SUCCESS(f'\n=== Cloning from BBS: {peer_url} ===\n'))

        # Step 1: Ensure peer is in trusted instances
        peer = TrustedInstance.objects.filter(web_ui_onion_url=peer_url, is_trusted_peer=True).first()
        if not peer:
            self.stdout.write(self.style.ERROR(
                f'Peer {peer_url} not found in trusted instances.\n'
                f'Please add it as a trusted peer in the admin interface first.'
            ))
            return

        # Step 2: Update peer's public key
        self.stdout.write('\n[1/5] Updating peer public key...')
        try:
            call_command('update_peer_key', peer_url)
            self.stdout.write(self.style.SUCCESS('  ✓ Public key updated'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Failed to update public key: {e}'))
            return

        # Step 3: Clone configuration (if not skipped)
        if not skip_config:
            self.stdout.write('\n[2/5] Cloning configuration from peer...')
            try:
                # Use the admin action logic via management command
                from io import StringIO
                import sys
                from core.services.service_manager import service_manager
                import requests
                import json

                sync_service = service_manager.sync_service
                if not sync_service or not sync_service.private_key:
                    self.stdout.write(self.style.ERROR('  ✗ Sync service not initialized'))
                    return

                target_url = f"{peer_url.strip('/')}/api/federation/export_config/"
                proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

                headers = sync_service._get_auth_headers()
                response = requests.get(target_url, headers=headers, proxies=proxies, timeout=120)

                if response.status_code != 200:
                    raise Exception(f"Peer returned status {response.status_code}")

                data = response.json()

                # Filter out superusers
                superuser_pks = {
                    obj['pk'] for obj in data
                    if obj['model'] == 'core.user' and obj['fields'].get('is_superuser')
                }

                filtered_objects = []
                for obj in data:
                    if obj['model'] == 'core.user' and obj['pk'] in superuser_pks:
                        continue

                    fields = obj.get('fields', {})
                    owner_pk = fields.get('owner')
                    user_pk = fields.get('user')
                    author_pk = fields.get('author')

                    if (owner_pk in superuser_pks or
                        user_pk in superuser_pks or
                        author_pk in superuser_pks):
                        continue

                    filtered_objects.append(obj)

                # Load data
                old_stdin = sys.stdin
                sys.stdin = StringIO(json.dumps(filtered_objects))
                try:
                    call_command('loaddata', '-', format='json', ignorenonexistent=True)
                finally:
                    sys.stdin = old_stdin

                call_command('backfill_avatars')

                self.stdout.write(self.style.SUCCESS('  ✓ Configuration cloned'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to clone configuration: {e}'))
                return
        else:
            self.stdout.write('\n[2/5] Skipping configuration clone')

        # Step 4: Clone applets (if not skipped)
        if not skip_applets:
            if backup_dir:
                # Restore from local backup
                self.stdout.write(f'\n[3/5] Restoring applets from backup: {backup_dir}')
                try:
                    call_command('restore_applets', backup_dir, '--skip-chunks', '--rekey')
                    self.stdout.write(self.style.SUCCESS('  ✓ Applets restored from backup'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed to restore applets: {e}'))
                    return
            else:
                # Sync from peer
                self.stdout.write('\n[3/5] Syncing applet manifests from peer...')
                try:
                    call_command('sync_applets_from_peer', '--peer', peer_url)
                    self.stdout.write(self.style.SUCCESS('  ✓ Applet manifests synced'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed to sync applet manifests: {e}'))
                    return

            # Step 5: Download applet chunks
            self.stdout.write('\n[4/5] Downloading applet chunks...')
            try:
                call_command('download_applet_chunks')
                self.stdout.write(self.style.SUCCESS('  ✓ Applet chunks downloaded'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to download chunks: {e}'))
                return
        else:
            self.stdout.write('\n[3/5] Skipping applet clone')
            self.stdout.write('[4/5] Skipping chunk download')

        # Step 6: Force refresh and re-key
        self.stdout.write('\n[5/5] Forcing refresh and re-key of all content...')
        try:
            from core.services.service_manager import service_manager
            from messaging.models import Message, PrivateMessage
            from core.models import FileAttachment
            from applets.models import Applet

            messages_updated = 0
            files_updated = 0
            pms_updated = 0
            applets_updated = 0

            for message in Message.objects.all():
                if message.metadata_manifest:
                    try:
                        message.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(message.metadata_manifest)
                        message.save()
                        messages_updated += 1
                    except Exception as e:
                        logger.error(f"Failed to rekey message {message.id}: {e}")

            for file_obj in FileAttachment.objects.all():
                if file_obj.metadata_manifest:
                    try:
                        file_obj.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(file_obj.metadata_manifest)
                        file_obj.save()
                        files_updated += 1
                    except Exception as e:
                        logger.error(f"Failed to rekey file {file_obj.id}: {e}")

            for pm in PrivateMessage.objects.all():
                if pm.metadata_manifest:
                    try:
                        pm.metadata_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(pm.metadata_manifest)
                        pm.save()
                        pms_updated += 1
                    except Exception as e:
                        logger.error(f"Failed to rekey PM {pm.id}: {e}")

            for applet in Applet.objects.all():
                if applet.code_manifest:
                    try:
                        applet.code_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(applet.code_manifest)
                        applet.save()
                        applets_updated += 1
                    except Exception as e:
                        logger.error(f"Failed to rekey applet {applet.id}: {e}")

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Re-keyed: {messages_updated} messages, {files_updated} files, '
                f'{pms_updated} PMs, {applets_updated} applets'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Failed to re-key content: {e}'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'✓ Clone complete!\n'
            f'{"="*60}\n'
            f'\nYour BBS is now cloned from {peer_url}\n'
            f'Content will continue to sync automatically via the background sync service.\n'
        ))
