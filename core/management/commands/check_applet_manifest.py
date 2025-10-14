# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7

from django.core.management.base import BaseCommand
from applets.models import Applet
from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum


class Command(BaseCommand):
    help = 'Check which keys are in an applet manifest'

    def add_arguments(self, parser):
        parser.add_argument('content_hash', type=str, help='Content hash of the applet to check')

    def handle(self, *args, **options):
        content_hash = options['content_hash']

        # Find applet
        applet = Applet.objects.filter(code_manifest__content_hash__startswith=content_hash).first()

        if not applet:
            self.stdout.write(self.style.ERROR(f'No applet found with hash starting with {content_hash}'))
            return

        self.stdout.write(f'\nApplet: {applet.name}')
        self.stdout.write(f'Full hash: {applet.code_manifest.get("content_hash")}')

        # Get local instance
        local_instance = TrustedInstance.objects.filter(
            encrypted_private_key__isnull=False,
            is_trusted_peer=False
        ).first()

        if local_instance:
            local_checksum = generate_checksum(local_instance.pubkey)
            self.stdout.write(f'\nLocal instance checksum: {local_checksum}')

        # Show all keys in manifest
        encrypted_keys = applet.code_manifest.get('encrypted_aes_keys', {})
        self.stdout.write(f'\nKeys in manifest ({len(encrypted_keys)} total):')

        for key_checksum in encrypted_keys.keys():
            is_local = '← LOCAL INSTANCE' if local_instance and key_checksum == local_checksum else ''
            self.stdout.write(f'  - {key_checksum} {is_local}')

        if local_instance and local_checksum not in encrypted_keys:
            self.stdout.write(self.style.ERROR('\n⚠️  LOCAL INSTANCE KEY NOT FOUND IN MANIFEST!'))
            self.stdout.write('This applet cannot be decrypted on this instance.')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Local instance key found in manifest'))
