#!/usr/bin/env python3
"""
Django management command to check and clean up problematic manifests.

Usage:
    python manage.py check_manifests                    # Check all manifests
    python manage.py check_manifests --test-decrypt     # Test decryption of all content
    python manage.py check_manifests --delete-bad       # Delete messages with bad manifests
    python manage.py check_manifests --content-hash abc123  # Check specific hash
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from messaging.models import Message, PrivateMessage
from core.models import FileAttachment
from applets.models import Applet
from core.services.service_manager import service_manager
import json


class Command(BaseCommand):
    help = 'Check and optionally clean up problematic manifests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-decrypt',
            action='store_true',
            help='Test decryption of all content to find bad manifests',
        )
        parser.add_argument(
            '--delete-bad',
            action='store_true',
            help='Delete messages/files with bad manifests (use with caution!)',
        )
        parser.add_argument(
            '--content-hash',
            type=str,
            help='Check a specific content hash',
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Show detailed manifest information',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('Manifest Health Check'))
        self.stdout.write(self.style.SUCCESS('='*70))

        if not service_manager.bitsync_service:
            from core.services.bitsync_service import BitSyncService
            service_manager.bitsync_service = BitSyncService()

        if not service_manager.sync_service:
            from core.services.sync_service import SyncService
            service_manager.sync_service = SyncService()

        # Statistics
        stats = {
            'messages': {'total': 0, 'bad': 0, 'good': 0},
            'private_messages': {'total': 0, 'bad': 0, 'good': 0},
            'attachments': {'total': 0, 'bad': 0, 'good': 0},
            'applets': {'total': 0, 'bad': 0, 'good': 0},
        }

        bad_items = []

        # Check Messages
        self.stdout.write('\nChecking Messages...')
        messages = Message.objects.all()
        if options['content_hash']:
            messages = messages.filter(metadata_manifest__content_hash__startswith=options['content_hash'])

        for msg in messages:
            stats['messages']['total'] += 1
            result = self._check_item(msg, 'message', msg.metadata_manifest, options)
            if not result['ok']:
                stats['messages']['bad'] += 1
                bad_items.append(('message', msg, result['error']))
            else:
                stats['messages']['good'] += 1

        # Check Private Messages
        self.stdout.write('\nChecking Private Messages...')
        pms = PrivateMessage.objects.all()
        if options['content_hash']:
            pms = pms.filter(metadata_manifest__content_hash__startswith=options['content_hash'])

        for pm in pms:
            stats['private_messages']['total'] += 1
            result = self._check_item(pm, 'private_message', pm.metadata_manifest, options)
            if not result['ok']:
                stats['private_messages']['bad'] += 1
                bad_items.append(('private_message', pm, result['error']))
            else:
                stats['private_messages']['good'] += 1

        # Check File Attachments
        self.stdout.write('\nChecking File Attachments...')
        attachments = FileAttachment.objects.all()
        if options['content_hash']:
            attachments = attachments.filter(metadata_manifest__content_hash__startswith=options['content_hash'])

        for att in attachments:
            stats['attachments']['total'] += 1
            result = self._check_item(att, 'attachment', att.metadata_manifest, options)
            if not result['ok']:
                stats['attachments']['bad'] += 1
                bad_items.append(('attachment', att, result['error']))
            else:
                stats['attachments']['good'] += 1

        # Check Applets
        self.stdout.write('\nChecking Applets...')
        applets = Applet.objects.all()
        if options['content_hash']:
            applets = applets.filter(code_manifest__content_hash__startswith=options['content_hash'])

        for applet in applets:
            stats['applets']['total'] += 1
            result = self._check_item(applet, 'applet', applet.code_manifest, options)
            if not result['ok']:
                stats['applets']['bad'] += 1
                bad_items.append(('applet', applet, result['error']))
            else:
                stats['applets']['good'] += 1

        # Print Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('='*70)

        for item_type, data in stats.items():
            self.stdout.write(f"\n{item_type.upper()}:")
            self.stdout.write(f"  Total: {data['total']}")
            self.stdout.write(self.style.SUCCESS(f"  Good: {data['good']}"))
            if data['bad'] > 0:
                self.stdout.write(self.style.ERROR(f"  Bad: {data['bad']}"))

        # Show bad items
        if bad_items:
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.ERROR(f'PROBLEMATIC ITEMS ({len(bad_items)} total)'))
            self.stdout.write('='*70)

            for item_type, item, error in bad_items:
                content_hash = self._get_content_hash(item, item_type)
                name = self._get_item_name(item, item_type)
                self.stdout.write(f"\n{item_type.upper()}: {name}")
                self.stdout.write(f"  Hash: {content_hash[:16]}...")
                self.stdout.write(self.style.ERROR(f"  Error: {error}"))

            # Delete if requested
            if options['delete_bad']:
                self.stdout.write('\n' + '='*70)
                self.stdout.write(self.style.WARNING('DELETING BAD ITEMS'))
                self.stdout.write('='*70)

                for item_type, item, error in bad_items:
                    name = self._get_item_name(item, item_type)
                    try:
                        item.delete()
                        self.stdout.write(self.style.SUCCESS(f"✓ Deleted {item_type}: {name}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"✗ Failed to delete {item_type}: {name} - {e}"))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ No problematic manifests found!'))

    def _check_item(self, item, item_type, manifest, options):
        """Check if an item's manifest is valid"""
        result = {'ok': True, 'error': None}

        if not manifest:
            result['ok'] = False
            result['error'] = 'No manifest'
            return result

        # Basic manifest structure check
        required_fields = ['content_hash', 'chunk_hashes', 'encryption_iv', 'encrypted_aes_keys']
        for field in required_fields:
            if field not in manifest:
                result['ok'] = False
                result['error'] = f'Missing field: {field}'
                return result

        # Show details if requested
        if options['show_details']:
            content_hash = manifest.get('content_hash', 'N/A')
            num_keys = len(manifest.get('encrypted_aes_keys', {}))
            num_chunks = len(manifest.get('chunk_hashes', []))
            self.stdout.write(f"  {self._get_item_name(item, item_type)}")
            self.stdout.write(f"    Hash: {content_hash[:16]}...")
            self.stdout.write(f"    Keys: {num_keys}, Chunks: {num_chunks}")

        # Test decryption if requested
        if options['test_decrypt']:
            try:
                decrypted = service_manager.sync_service.get_decrypted_content(manifest)
                if not decrypted:
                    result['ok'] = False
                    result['error'] = 'Decryption failed (no data returned)'
                else:
                    # Try to parse as JSON
                    try:
                        data = json.loads(decrypted)
                        # Verify it has expected structure
                        if 'type' not in data:
                            result['ok'] = False
                            result['error'] = 'Decrypted data missing "type" field'
                    except json.JSONDecodeError as e:
                        result['ok'] = False
                        result['error'] = f'Decrypted data is not valid JSON: {e}'
            except Exception as e:
                result['ok'] = False
                result['error'] = f'Decryption exception: {e}'

        return result

    def _get_content_hash(self, item, item_type):
        """Get content hash from an item"""
        if item_type == 'applet':
            return item.code_manifest.get('content_hash', 'N/A')
        else:
            return item.metadata_manifest.get('content_hash', 'N/A')

    def _get_item_name(self, item, item_type):
        """Get a human-readable name for an item"""
        if item_type == 'message':
            return f"'{item.subject}' by {item.author.username if item.author else 'Unknown'}"
        elif item_type == 'private_message':
            return f"PM from {item.sender.username if item.sender else 'Unknown'}"
        elif item_type == 'attachment':
            return f"'{item.filename}'"
        elif item_type == 'applet':
            return f"'{item.name}'"
        return 'Unknown'
