# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/services/sync_service.py
import threading
import time
import requests
import logging
import json
import base64
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from functools import partial

from django.utils import timezone as django_timezone
from django.conf import settings
from django.core.files.base import ContentFile
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from django.db import IntegrityError
import uuid

from core.models import TrustedInstance, FileAttachment, User
from messaging.models import Message, PrivateMessage, MessageBoard
from applets.models import Applet, AppletData
from federation.models import FederatedAction
from accounts.models import BannedPubkey
from core.services.encryption_utils import generate_checksum, generate_short_id, decrypt_for_recipients_only
from accounts.avatar_generator import generate_cow_avatar

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, poll_interval=120):
        self.poll_interval = poll_interval
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.local_instance = None
        self.private_key = None
        max_file_downloads = getattr(settings, 'BITSYNC_MAX_CONCURRENT_FILES', 3)
        self.download_executor = ThreadPoolExecutor(max_workers=max_file_downloads, thread_name_prefix='download_worker')
        self.currently_downloading = set()

    def start(self):
        self.thread.start()
        logger.info("BitSync Service thread started. Polling will begin shortly.")

    def _run(self):
        time.sleep(30)
        logger.info("SyncService polling loop is now active.")
        while True:
            try:
                self._load_identity()
                if self.local_instance and self.private_key:
                    self._resume_incomplete_downloads()
                    self.poll_peers()
                else:
                    logger.warning("Sync service cannot run without a configured local instance identity. Will check again in %s seconds.", self.poll_interval)
            except Exception as e:
                logger.error(f"Error in sync service poll loop: {e}", exc_info=True)
            
            time.sleep(self.poll_interval)
    
    def _load_identity(self):
        try:
            self.local_instance = TrustedInstance.objects.filter(
                encrypted_private_key__isnull=False,
                is_trusted_peer=False
            ).first()

            if self.local_instance and self.local_instance.encrypted_private_key:
                key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
                from cryptography.fernet import Fernet
                f = Fernet(key)
                decrypted_pem = f.decrypt(self.local_instance.encrypted_private_key.encode())
                self.private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
        except Exception as e:
            logger.error(f"Failed to load local identity for sync service: {e}")
            self.local_instance, self.private_key = None, None

    def _resume_incomplete_downloads(self):
        from .service_manager import service_manager
        logger.info("Checking for any incomplete downloads to resume...")
        
        all_content = list(FileAttachment.objects.all()) + \
                      list(Message.objects.filter(metadata_manifest__isnull=False)) + \
                      list(PrivateMessage.objects.filter(metadata_manifest__isnull=False))
        
        incomplete_items = [
            item for item in all_content
            if item.metadata_manifest and not service_manager.bitsync_service.are_all_chunks_local(item.metadata_manifest)
        ]
        
        for item in incomplete_items:
            self._schedule_download(item.metadata_manifest)
        
        if not incomplete_items:
            logger.info("No incomplete downloads found.")

    def _get_auth_headers(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        hasher = hashlib.sha256(timestamp.encode('utf-8'))
        digest = hasher.digest()
        signature = self.private_key.sign(
            digest, rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH), hashes.SHA256()
        )
        return {
            'X-Pubkey': base64.b64encode(self.local_instance.pubkey.encode('utf-8')).decode('utf-8'),
            'X-Timestamp': timestamp,
            'X-Signature': base64.b64encode(signature).decode('utf-8')
        }

    def poll_peers(self):
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        if not peers.exists(): return
        
        logger.info(f"Beginning to poll {peers.count()} peer(s) for new content...")
        for peer in peers:
            if not peer.web_ui_onion_url: continue
            
            last_sync = peer.last_synced_at - timedelta(minutes=10) if peer.last_synced_at else datetime.min.replace(tzinfo=timezone.utc)
            proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
            
            server_timestamp_str = None
            try:
                target_url = f"{peer.web_ui_onion_url.strip('/')}/api/sync/?since={last_sync.isoformat()}"
                response = requests.get(target_url, headers=self._get_auth_headers(), proxies=proxies, timeout=120)
                
                if response.status_code == 200:
                    response_data = response.json()
                    manifests = response_data.get('manifests', [])
                    federated_actions = response_data.get('federated_actions', [])
                    server_timestamp_str = response_data.get('server_timestamp')

                    logger.info(f"<-- Received {len(manifests)} new manifest(s) and {len(federated_actions)} action(s) from peer {peer.web_ui_onion_url}")
                    if manifests:
                        self._process_received_manifests(manifests)
                    if federated_actions:
                        self._process_received_actions(federated_actions)
                else:
                    logger.warning(f"<-- Failed to sync with peer {peer.web_ui_onion_url}: Status {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                logger.error(f"<-- Network error while contacting peer {peer.web_ui_onion_url}: {e}")

            finally:
                peer.last_synced_at = django_timezone.datetime.fromisoformat(server_timestamp_str) if server_timestamp_str else django_timezone.now()
                peer.save()
                logger.info(f"Timestamp for peer {peer.web_ui_onion_url} updated to {peer.last_synced_at.isoformat()}")

    def _download_done_callback(self, manifest, future):
        content_hash = manifest.get('content_hash')
        self.currently_downloading.discard(content_hash)
        try:
            encrypted_data = future.result()
            if encrypted_data:
                self._process_completed_download(manifest, encrypted_data)
        except Exception as e:
            logger.error(f"Download failed for {content_hash[:10]}... with error: {e}")

    def _schedule_download(self, manifest):
        content_hash = manifest.get('content_hash')
        if not content_hash or content_hash in self.currently_downloading: return
        
        item_name = manifest.get('filename', content_hash[:16])
        logger.info(f"Scheduling download for: '{item_name}' ({content_hash[:10]}...)")
        self.currently_downloading.add(content_hash)
        
        future = self.download_executor.submit(self._download_content, manifest)
        future.add_done_callback(partial(self._download_done_callback, manifest))

    def _process_received_manifests(self, manifests: list):
        from .service_manager import service_manager

        for manifest in manifests:
            content_hash = manifest.get('content_hash')
            if not content_hash: continue

            # Check if content already exists and update manifests if needed
            existing_message = Message.objects.filter(metadata_manifest__content_hash=content_hash).first()
            existing_file = FileAttachment.objects.filter(metadata_manifest__content_hash=content_hash).first()
            existing_pm = PrivateMessage.objects.filter(metadata_manifest__content_hash=content_hash).first()
            existing_applet = Applet.objects.filter(code_manifest__content_hash=content_hash).first()

            if existing_message or existing_file or existing_pm or existing_applet:
                # Content exists - check if manifest needs updating
                try:
                    # Get the current manifest from the database
                    if existing_message:
                        current_manifest = existing_message.metadata_manifest
                        existing_obj = existing_message
                    elif existing_file:
                        current_manifest = existing_file.metadata_manifest
                        existing_obj = existing_file
                    elif existing_pm:
                        current_manifest = existing_pm.metadata_manifest
                        existing_obj = existing_pm
                    else:  # existing_applet
                        current_manifest = existing_applet.code_manifest
                        existing_obj = existing_applet

                    # Check if content was rekeyed (different IV = different encryption)
                    current_iv = current_manifest.get('encryption_iv')
                    incoming_iv = manifest.get('encryption_iv')

                    if current_iv != incoming_iv:
                        # Content was rekeyed! Delete the existing record and re-download
                        logger.info(f"Rekey detected for {content_hash[:10]}... (IV changed). Deleting existing record and re-downloading.")
                        existing_obj.delete()
                        # Clear cached chunks will be handled by detect_and_clear_rekeyed_chunks in _download_content
                        self._schedule_download(manifest)
                    else:
                        # Check if the incoming manifest has any new encryption keys
                        current_keys = set(current_manifest.get('encrypted_aes_keys', {}).keys())
                        incoming_keys = set(manifest.get('encrypted_aes_keys', {}).keys())

                        # Only update if there are new keys we don't have
                        if not incoming_keys.issubset(current_keys):
                            # New keys detected - merge them in
                            updated_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(manifest)

                            if existing_message:
                                existing_message.metadata_manifest = updated_manifest
                                existing_message.save()
                                logger.info(f"Updated manifest for existing message {content_hash[:10]} (added {len(incoming_keys - current_keys)} new key(s))")
                            elif existing_file:
                                existing_file.metadata_manifest = updated_manifest
                                existing_file.save()
                                logger.info(f"Updated manifest for existing file {content_hash[:10]} (added {len(incoming_keys - current_keys)} new key(s))")
                            elif existing_pm:
                                existing_pm.metadata_manifest = updated_manifest
                                existing_pm.save()
                                logger.info(f"Updated manifest for existing PM {content_hash[:10]} (added {len(incoming_keys - current_keys)} new key(s))")
                            elif existing_applet:
                                existing_applet.code_manifest = updated_manifest
                                existing_applet.save()
                                logger.info(f"Updated manifest for existing applet {content_hash[:10]} (added {len(incoming_keys - current_keys)} new key(s))")
                        # else: No new keys, skip update
                except Exception as e:
                    logger.error(f"Failed to update manifest for {content_hash[:10]}: {e}")
            else:
                # New content - schedule download
                self._schedule_download(manifest)

    def _process_received_actions(self, actions: list):
        for action_data in actions:
            action_id = action_data.get('id')
            if FederatedAction.objects.filter(id=action_id).exists():
                continue

            action_type = action_data.get('action_type')
            logger.info(f"Processing federated action: {action_type} ({action_id})")

            try:
                FederatedAction.objects.create(
                    id=action_id,
                    action_type=action_type,
                    pubkey_target=action_data.get('pubkey_target'),
                    content_hash_target=action_data.get('content_hash_target'),
                    action_details=action_data.get('action_details', {}),
                    created_at=django_timezone.datetime.fromisoformat(action_data.get('created_at'))
                )

                if action_type == 'ban_pubkey':
                    pubkey = action_data.get('pubkey_target')
                    details = action_data.get('action_details', {})
                    is_temporary = details.get('is_temporary', False)
                    duration = details.get('duration_hours')
                    expires_at = None
                    if is_temporary and duration:
                        expires_at = django_timezone.now() + timedelta(hours=int(duration))
                    
                    BannedPubkey.objects.update_or_create(
                        pubkey=pubkey,
                        defaults={
                            'is_temporary': is_temporary,
                            'expires_at': expires_at,
                            'federated_action_id': action_id
                        }
                    )
                    logger.info(f"Federated ban applied for pubkey: {pubkey[:12]}...")

                elif action_type == 'unpin_content':
                    content_hash = action_data.get('content_hash_target')
                    Message.objects.filter(metadata_manifest__content_hash=content_hash).update(is_pinned=False, pinned_by=None)
                    FileAttachment.objects.filter(metadata_manifest__content_hash=content_hash).update(is_pinned=False, pinned_by=None)
                    logger.info(f"Federated unpin applied for content hash: {content_hash[:12]}...")

                elif action_type == 'DELETE_CONTENT':
                    content_hash = action_data.get('content_hash_target')
                    if content_hash:
                        Message.objects.filter(metadata_manifest__content_hash=content_hash).delete()
                        logger.info(f"Applied federated delete for content hash: {content_hash[:12]}...")

                elif action_type == 'update_profile':
                    pubkey = action_data.get('pubkey_target')
                    details = action_data.get('action_details', {})
                    user_to_update = User.objects.filter(pubkey=pubkey).first()
                    
                    if user_to_update:
                        user_to_update.nickname = details.get('nickname', user_to_update.nickname)
                        user_to_update.karma = details.get('karma', user_to_update.karma)
                        user_to_update.save()
                        logger.info(f"Applied federated profile update for user: {user_to_update.username}")
                        
                        avatar_hash = details.get('avatar_hash')
                        if avatar_hash:
                            manifest_to_download = self.get_manifest_by_content_hash(avatar_hash)
                            if manifest_to_download:
                                self._schedule_download(manifest_to_download)
                            else:
                                logger.warning(f"Avatar hash {avatar_hash} was specified, but no corresponding manifest was received. A full sync may be required.")
                            self._apply_avatar_from_hash(user_to_update, avatar_hash)

            except Exception as e:
                logger.error(f"Failed to process federated action {action_id}: {e}", exc_info=True)

    def _process_completed_download(self, manifest, encrypted_data):
        from .service_manager import service_manager
        content_hash = manifest.get('content_hash')

        if Message.objects.filter(metadata_manifest__content_hash=content_hash).exists() or \
           FileAttachment.objects.filter(metadata_manifest__content_hash=content_hash).exists() or \
           PrivateMessage.objects.filter(metadata_manifest__content_hash=content_hash).exists():
            return

        logger.info(f"Processing newly completed download for hash {content_hash[:10]}...")
        decrypted_data = self._decrypt_data(encrypted_data, manifest)
        if not decrypted_data: return

        try:
            final_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(manifest)
            logger.info(f"Manifest {content_hash[:10]} successfully re-keyed for local peers.")
        except Exception as e:
            logger.error(f"Failed to re-key manifest for {content_hash[:10]}, aborting save. Error: {e}")
            return
        
        content_type = final_manifest.get('content_type')
        try:
            content = json.loads(decrypted_data)

            if content_type == 'message':
                required_hashes = content.get('attachment_hashes', [])
                if required_hashes:
                    existing_attachments = FileAttachment.objects.filter(metadata_manifest__content_hash__in=required_hashes)
                    if len(existing_attachments) != len(required_hashes):
                        logger.warning(f"Message {content_hash[:10]} is waiting for attachments to download. Will retry processing later.")
                        return
                
                author_pubkey = content.get('pubkey')
                if author_pubkey:
                    short_id = generate_short_id(author_pubkey, length=8)
                    defaults = {
                        'nickname': f"Moo-{short_id}",
                        'is_active': False,
                        'password': User.objects.make_random_password()
                    }
                    try:
                        new_user, created = User.objects.get_or_create(pubkey=author_pubkey, defaults={**defaults, 'username': f"federated_{short_id}"})
                        if created:
                            avatar_content_file, avatar_filename = generate_cow_avatar(author_pubkey)
                            new_user.avatar.save(avatar_filename, avatar_content_file, save=True)
                            logger.info(f"Discovered new federated user. Created profile '{new_user.nickname}' with a unique cow avatar.")
                    except IntegrityError:
                        random_suffix = uuid.uuid4().hex[:4]
                        new_user, created = User.objects.get_or_create(pubkey=author_pubkey, defaults={**defaults, 'username': f"federated_{short_id}_{random_suffix}", 'nickname': f"Moo-{short_id}-{random_suffix}"})
                        if created:
                            logger.info(f"Created federated user with fallback nickname '{new_user.nickname}'.")
                
                board, _ = MessageBoard.objects.get_or_create(name=content.get('board', 'general'))
                message = Message.objects.create(
                    board=board, subject=content.get('subject'), body=content.get('body'),
                    pubkey=content.get('pubkey'), metadata_manifest=final_manifest
                )

                if required_hashes:
                    message.attachments.set(existing_attachments)
                
                logger.info(f"Successfully saved new message: '{message.subject}'")

            elif content_type == 'file':
                # Check if file has an author pubkey and auto-create federated user if needed
                author_pubkey = content.get('pubkey')
                author_user = None
                if author_pubkey:
                    short_id = generate_short_id(author_pubkey, length=8)
                    # Use nickname from content if available, otherwise fallback to Moo-{short_id}
                    federated_nickname = content.get('nickname', f"Moo-{short_id}")
                    original_username = content.get('username')  # Username from their home BBS

                    defaults = {
                        'nickname': federated_nickname,
                        'is_active': False,
                        'password': User.objects.make_random_password()
                    }
                    try:
                        author_user, created = User.objects.get_or_create(
                            pubkey=author_pubkey,
                            defaults={**defaults, 'username': f"federated_{short_id}"}
                        )
                        if created:
                            logger.info(f"Discovered new federated user via file upload. Created profile '{author_user.nickname}' (home username: {original_username}).")
                    except IntegrityError:
                        random_suffix = uuid.uuid4().hex[:4]
                        author_user, created = User.objects.get_or_create(
                            pubkey=author_pubkey,
                            defaults={**defaults, 'username': f"federated_{short_id}_{random_suffix}", 'nickname': f"{federated_nickname}-{random_suffix}"}
                        )
                        if created:
                            logger.info(f"Created federated user with fallback nickname '{author_user.nickname}'.")

                attachment = FileAttachment.objects.create(
                    filename=content.get('filename', 'unknown'),
                    content_type=content.get('content_type', 'application/octet-stream'),
                    size=content.get('size', 0),
                    author=author_user,
                    metadata_manifest=final_manifest
                )
                logger.info(f"Successfully saved new file: '{content.get('filename')}'")

                # If this is an avatar file (cow_*.png) and we just created the user, apply it as their avatar
                if author_user and content.get('filename', '').startswith('cow_'):
                    try:
                        image_bytes = base64.b64decode(content.get('data'))
                        content_file = ContentFile(image_bytes, name=content.get('filename'))
                        author_user.avatar.save(content.get('filename'), content_file, save=True)
                        logger.info(f"Applied federated avatar for user '{author_user.nickname}'")
                    except Exception as e:
                        logger.error(f"Failed to apply avatar for federated user: {e}")

                pending_actions = FederatedAction.objects.filter(
                    action_type='update_profile',
                    action_details__avatar_hash=content_hash
                )
                for action in pending_actions:
                    user_to_update = User.objects.filter(pubkey=action.pubkey_target).first()
                    if user_to_update:
                        self._apply_avatar_from_attachment(user_to_update, attachment)

            elif content_type == 'pm':
                recipient_pubkey_checksum = content.get('recipient_pubkey_checksum')
                
                local_user_pubkeys = User.objects.filter(is_active=True).values_list('pubkey', flat=True)
                local_user_checksums = {generate_checksum(pk) for pk in local_user_pubkeys if pk}

                if recipient_pubkey_checksum in local_user_checksums:
                    e2e_content_b64 = content.get('e2e_encrypted_content_b64')
                    if not e2e_content_b64:
                        logger.error("Downloaded PM manifest is missing the E2E content payload.")
                        return

                    recipient_pubkey = content.get('recipient_pubkey')
                    if not recipient_pubkey:
                        logger.warning(f"PM received without a recipient public key. Discarding.")
                        return

                    recipient_user, created = User.objects.get_or_create(
                        pubkey=recipient_pubkey,
                        defaults={
                            'username': f"federated_{generate_short_id(recipient_pubkey, 8)}",
                            'is_active': False
                        }
                    )
                
                    if created:
                        logger.info(f"Created new federated user profile for PM recipient: {recipient_user.username}")

                    PrivateMessage.objects.create(
                        recipient=recipient_user,
                        sender_pubkey=content.get('sender_pubkey'),
                        e2e_encrypted_content=e2e_content_b64,
                        metadata_manifest=final_manifest
                    )
                    logger.info(f"Successfully received and saved a federated E2E PM for user '{recipient_user.username}'.")
                else:
                    logger.info(f"Received PM metadata for a different BBS. Ignoring.")

        except Exception as e:
            logger.error(f"Failed to create database object from manifest {content_hash[:10]}: {e}", exc_info=True)
    
    def _find_seeders(self, content_hash: str) -> list:
        logger.info(f"Discovering seeders for content {content_hash[:10]}...")
        available_seeders = []
        peers = TrustedInstance.objects.filter(is_trusted_peer=True)
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        for peer in peers:
            if not peer.web_ui_onion_url: continue
            try:
                url = f"{peer.web_ui_onion_url.strip('/')}/api/bitsync/has_content/{content_hash}/"
                response = requests.get(url, headers=self._get_auth_headers(), proxies=proxies, timeout=60)
                if response.status_code == 200:
                    available_seeders.append(peer.web_ui_onion_url)
            except requests.RequestException:
                logger.warning(f"Could not contact peer {peer.web_ui_onion_url} to check for content.")
        return available_seeders

    def _download_content(self, manifest: dict) -> bytes | None:
        content_hash, chunk_hashes = manifest['content_hash'], manifest['chunk_hashes']
        num_chunks = len(chunk_hashes)
        item_name = manifest.get('filename', content_hash[:16])
        from .service_manager import service_manager

        # Check if content was rekeyed and clear stale chunks if needed
        service_manager.bitsync_service.detect_and_clear_rekeyed_chunks(manifest)

        if service_manager.bitsync_service.are_all_chunks_local(manifest):
            local_chunks_data = b""
            for i in range(num_chunks):
                chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, i)
                try:
                    with open(chunk_path, 'rb') as f:
                        local_chunks_data += f.read()
                except FileNotFoundError:
                    break
            else:
                # Save manifest cache for future rekey detection
                service_manager.bitsync_service.save_manifest_cache(manifest)
                return local_chunks_data

        seeders = self._find_seeders(content_hash)
        if not seeders:
            logger.error(f"Cannot download '{item_name}': No seeders found.")
            return None

        logger.info(f"Starting swarm download for '{item_name}' from {len(seeders)} peer(s).")
        downloaded_chunks = {}
        for i in range(num_chunks):
            chunk_path = service_manager.bitsync_service.get_chunk_path(content_hash, i)
            if chunk_path and os.path.exists(chunk_path):
                 with open(chunk_path, 'rb') as f:
                    downloaded_chunks[i] = f.read()

        
        proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
        chunks_to_download = [i for i in range(num_chunks) if i not in downloaded_chunks]
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix='chunk_worker') as executor:
            futures = {
                executor.submit(self._download_chunk, seeders[i % len(seeders)], content_hash, chunk_idx, proxies): chunk_idx
                for i, chunk_idx in enumerate(chunks_to_download)
            }
            for future in as_completed(futures):
                chunk_index, chunk_data = future.result()
                if chunk_data and hashlib.sha256(chunk_data).hexdigest() == chunk_hashes[chunk_index]:
                    downloaded_chunks[chunk_index] = chunk_data
                    chunk_save_path = service_manager.bitsync_service.get_chunk_path(content_hash, chunk_index)
                    if chunk_save_path:
                         os.makedirs(os.path.dirname(chunk_save_path), exist_ok=True)
                         with open(chunk_save_path, 'wb') as f:
                             f.write(chunk_data)
                    logger.info(f"  - Chunk {chunk_index + 1}/{num_chunks} for '{item_name}' downloaded.")
                else: 
                     logger.error(f"   - Failed to download/verify chunk {chunk_index + 1} for '{item_name}'. Will retry on next sync.")
        
        if len(downloaded_chunks) == num_chunks:
            logger.info(f"Download complete for '{item_name}'.")
            # Save manifest cache for future rekey detection
            service_manager.bitsync_service.save_manifest_cache(manifest)
            return b"".join(downloaded_chunks[i] for i in range(num_chunks))
        else:
            logger.error(f"Download for '{item_name}' is incomplete. Will retry on next sync cycle.")
            return None
    
    def _download_content_by_hash(self, content_hash: str) -> bytes | None:
        """Helper to download a file by its hash directly, assuming a manifest exists."""
        from .service_manager import service_manager
        manifest = self.get_manifest_by_content_hash(content_hash)
        if not manifest:
            logger.warning(f"Could not find a manifest for content hash {content_hash[:10]}... to download.")
            return None
        
        return self._download_content(manifest)

    def get_manifest_by_content_hash(self, content_hash: str):
        """Searches for a manifest across all models by content hash."""
        for model in [Message, FileAttachment, PrivateMessage, Applet, AppletData]:
            field_name = 'metadata_manifest'
            if not hasattr(model, field_name):
                field_name = 'code_manifest' if hasattr(model, 'code_manifest') else 'data_manifest'
                if not hasattr(model, field_name):
                    continue

            obj = model.objects.filter(**{f'{field_name}__content_hash': content_hash}).first()
            if obj:
                return getattr(obj, field_name)
        
        return None
    
    def _download_chunk(self, seeder_url, content_hash, chunk_index, proxies):
        try:
            url = f"{seeder_url.strip('/')}/api/bitsync/chunk/{content_hash}/{chunk_index}/"
            response = requests.get(url, headers=self._get_auth_headers(), proxies=proxies, timeout=120)
            if response.status_code == 200: return chunk_index, response.content
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download chunk {chunk_index} from {seeder_url}: {e}")
            return chunk_index, None

    def _decrypt_data(self, encrypted_data: bytes, manifest: dict) -> bytes | None:
        if not encrypted_data: return None
        try:
            if not self.local_instance or not self.local_instance.pubkey:
                logger.warning("Local instance or its public key is not loaded, cannot decrypt content.")
                return None

            local_checksum = generate_checksum(self.local_instance.pubkey)
            encrypted_aes_key_b64 = manifest['encrypted_aes_keys'].get(local_checksum)
            if not encrypted_aes_key_b64:
                logger.error("Could not find an encryption envelope for our key in the manifest.")
                return None
            encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
            aes_key = self.private_key.decrypt(
                encrypted_aes_key,
                rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
            )
            iv = base64.b64decode(manifest['encryption_iv'])
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            unpadder = PKCS7(algorithms.AES.block_size).unpadder()
            return unpadder.update(padded_data) + unpadder.finalize()
        except Exception as e:
            logger.error(f"Failed to decrypt content {manifest['content_hash'][:10]}...: {e}", exc_info=True)
            return None

    def get_decrypted_content(self, manifest: dict) -> bytes | None:
        if not self.private_key:
            self._load_identity()
        
        if not self.private_key:
            logger.error("Cannot decrypt content because local instance identity is not loaded.")
            return None

        content_hash = manifest.get('content_hash')
        if content_hash in self.currently_downloading:
            logger.info("Content is being downloaded by the background service; UI download will wait.")
        encrypted_data = self._download_content(manifest)
        if encrypted_data:
            return self._decrypt_data(encrypted_data, manifest)
        return None

    def _apply_avatar_from_hash(self, user, avatar_hash):
        """Finds a local attachment by hash and applies it as a user's avatar."""
        try:
            attachment = FileAttachment.objects.get(metadata_manifest__content_hash=avatar_hash)
            self._apply_avatar_from_attachment(user, attachment)
        except FileAttachment.DoesNotExist:
            logger.info(f"Avatar for user {user.username} (hash: {avatar_hash[:10]}) is not yet local. Will apply after download.")
    
    def _apply_avatar_from_attachment(self, user, attachment):
        """Given a user and a FileAttachment, decrypts the file and saves it as the user's avatar."""
        try:
            logger.info(f"Attempting to apply new federated avatar {attachment.filename} to user {user.username}")
            encrypted_data = self._download_content(attachment.metadata_manifest)
            if not encrypted_data:
                logger.warning(f"Could not get encrypted data for avatar {attachment.filename}.")
                return

            decrypted_data = self._decrypt_data(encrypted_data, attachment.metadata_manifest)
            if not decrypted_data:
                logger.warning(f"Could not decrypt data for avatar {attachment.filename}.")
                return
            
            try:
                payload = json.loads(decrypted_data.decode('utf-8'))
                image_bytes = base64.b64decode(payload.get('data'))
                content_file = ContentFile(image_bytes, name=attachment.filename)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse payload for avatar {attachment.filename}: {e}")
                return

            user.avatar.save(attachment.filename, content_file, save=True)
            logger.info(f"Successfully applied new federated avatar for user {user.username}.")
        except Exception as e:
            logger.error(f"Failed to apply avatar {attachment.filename} to user {user.username}: {e}")

# Subtle change for git sync
