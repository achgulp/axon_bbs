"""
Management command to post applet updates to the Applet Library board.

Usage:
    python manage.py post_applet_update <applet_js_path> --name "Applet Name" --description "Description"
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import User, FileAttachment
from messaging.models import MessageBoard, Message
from applets.models import Applet
from core.services.service_manager import service_manager
import hashlib
import os
import json
import base64


class Command(BaseCommand):
    help = 'Post an applet update to the Applet Library message board'

    def add_arguments(self, parser):
        parser.add_argument('applet_path', type=str, help='Path to the applet JavaScript file')
        parser.add_argument('--name', type=str, required=True, help='Applet name')
        parser.add_argument('--description', type=str, default='', help='Applet description')
        parser.add_argument('--username', type=str, default='Achduke7', help='Username to post as')
        parser.add_argument('--board', type=str, default='Applet Library', help='Board name to post to')

    def handle(self, *args, **options):
        applet_path = options['applet_path']
        applet_name = options['name']
        description = options['description']
        username = options['username']
        board_name = options['board']

        # Validate file exists
        if not os.path.exists(applet_path):
            self.stdout.write(self.style.ERROR(f'File not found: {applet_path}'))
            return

        # Read applet file
        with open(applet_path, 'rb') as f:
            applet_content = f.read()

        # Calculate hash
        file_hash = hashlib.sha256(applet_content).hexdigest()

        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found. Please create the user first.'))
            return

        # Get or create message board
        board, created = MessageBoard.objects.get_or_create(
            name=board_name,
            defaults={
                'description': 'Repository of applet updates and manifests'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created message board: {board_name}'))

        # Check if this exact version already exists
        existing = FileAttachment.objects.filter(
            filename=os.path.basename(applet_path),
            size=len(applet_content)
        ).first()

        if existing and existing.metadata_manifest.get('content_hash'):
            # Check if already posted
            existing_message = Message.objects.filter(
                attachments=existing,
                board=board
            ).first()
            if existing_message:
                self.stdout.write(self.style.WARNING(
                    f'This applet version already posted: {existing_message.subject}'
                ))
                self.stdout.write(self.style.WARNING(
                    f'Message ID: {existing_message.id}'
                ))
                return

        # Create proper BitSync manifest using the service
        filename = os.path.basename(applet_path)

        file_content_payload = {
            "type": "file",
            "filename": filename,
            "content_type": "application/javascript",
            "size": len(applet_content),
            "data": base64.b64encode(applet_content).decode('ascii'),
            "applet_name": applet_name,
            "description": description
        }

        try:
            # Import and initialize BitSyncService if not available
            if not service_manager.bitsync_service:
                from core.services.bitsync_service import BitSyncService
                service_manager.bitsync_service = BitSyncService()
                self.stdout.write(self.style.SUCCESS('Initialized BitSyncService'))

            content_hash, bitsync_manifest = service_manager.bitsync_service.create_encrypted_content(file_content_payload)
            self.stdout.write(self.style.SUCCESS(f'Created BitSync manifest with content_hash: {content_hash[:16]}...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create BitSync manifest: {e}'))
            import traceback
            traceback.print_exc()
            return

        # Create attachment with proper BitSync manifest
        attachment = FileAttachment.objects.create(
            author=user,
            filename=filename,
            content_type='application/javascript',
            size=len(applet_content),
            metadata_manifest=bitsync_manifest
        )

        self.stdout.write(self.style.SUCCESS(f'Created FileAttachment ID: {attachment.id}'))

        # Create message body
        message_body = f'''**{applet_name}** - Update

{description}

**Applet Manifest:**
```json
{{
  "name": "{applet_name}",
  "description": "{description}",
  "version": "1.0",
  "js_hash": "{file_hash}",
  "dependencies": [
    "three",
    "jszip"
  ]
}}
```

**Installation:**
1. Download the attached {filename}
2. Go to Admin Console → Applets
3. Find "{applet_name}" and click Edit
4. Update the manifest with the JSON above
5. Upload the attached .js file
6. Save

**File Hash:** `{file_hash}`
**FileAttachment ID:** {attachment.id}
'''

        # Create BitSync manifest for the message content itself (required for federation sync)
        message_content_payload = {
            "type": "message",
            "subject": f"{applet_name} [{bitsync_manifest.get('content_hash', '')[:8]}]",
            "body": message_body,
            "board": board.name,
            "pubkey": user.pubkey,
            "attachment_hashes": [bitsync_manifest.get('content_hash')]
        }

        try:
            message_content_hash, message_manifest = service_manager.bitsync_service.create_encrypted_content(message_content_payload)
            self.stdout.write(self.style.SUCCESS(f'Created message BitSync manifest: {message_content_hash[:16]}...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create message manifest: {e}'))
            message_manifest = None

        # Create message
        # Use first 8 digits of content hash for unique identification
        hash_prefix = bitsync_manifest.get('content_hash', '')[:8]
        message = Message.objects.create(
            board=board,
            author=user,
            subject=f"{applet_name} [{hash_prefix}]",
            body=message_body,
            metadata_manifest=message_manifest  # Add manifest for federation sync
        )
        message.attachments.add(attachment)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Posted applet update to "{board_name}" board'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  Message ID: {message.id}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  Subject: {message.subject}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  Attachment Hash: {file_hash}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  FileAttachment ID: {attachment.id}'
        ))

        # Update the applet's code manifest to use the new FileAttachment
        # Try multiple strategies to find the applet
        applet = None
        matched_by = None
        
        # Strategy 1: Exact name match
        try:
            applet = Applet.objects.get(name=applet_name)
            matched_by = "exact name"
        except Applet.DoesNotExist:
            pass
        
        # Strategy 2: Match by filename (e.g., AiRobotWars.js -> AiRobotWars)
        if not applet:
            filename_without_ext = os.path.splitext(filename)[0]
            try:
                applet = Applet.objects.get(name=filename_without_ext)
                matched_by = f"filename '{filename_without_ext}'"
            except Applet.DoesNotExist:
                pass
        
        # Strategy 3: Case-insensitive name match
        if not applet:
            try:
                applet = Applet.objects.get(name__iexact=applet_name)
                matched_by = f"case-insensitive match '{applet.name}'"
            except Applet.DoesNotExist:
                pass
            except Applet.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(
                    f'\n⚠ Multiple applets match "{applet_name}" (case-insensitive). Skipping update.'
                ))
        
        # Strategy 4: Partial name match (contains)
        if not applet:
            matches = Applet.objects.filter(name__icontains=applet_name.replace(' ', ''))
            if matches.count() == 1:
                applet = matches.first()
                matched_by = f"partial match '{applet.name}'"
            elif matches.count() > 1:
                self.stdout.write(self.style.WARNING(
                    f'\n⚠ Multiple applets partially match "{applet_name}": {[a.name for a in matches]}'
                ))
        
        if applet:
            # The code_manifest needs to reference the FileAttachment's metadata_manifest
            # which is stored as a BitSync manifest
            applet.code_manifest = attachment.metadata_manifest
            applet.save()

            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Updated "{applet.name}" applet code manifest (matched by {matched_by})'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'  Applet ID: {applet.id}'
            ))
        else:
            # List available applets to help user find the right name
            available_applets = list(Applet.objects.values_list('name', flat=True))
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Applet "{applet_name}" not found in database. Skipping applet update.'
            ))
            self.stdout.write(self.style.WARNING(
                f'  Available applets: {available_applets}'
            ))
            self.stdout.write(self.style.WARNING(
                f'  You can manually create it in the admin console or use one of the above names.'
            ))
