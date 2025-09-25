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


# Full path: axon_bbs/federation/uat_verifier_agent_service.py
import threading
import time
import logging
import json
import base64
import os
from django.utils import timezone
from django.conf import settings

from core.models import User, FileAttachment
from messaging.models import Message, MessageBoard, PrivateMessage
from federation.models import FederatedAction
from accounts.models import Alias
from core.services.sync_service import SyncService
from core.services.encryption_utils import generate_checksum
from core.services.bitsync_service import BitSyncService

logger = logging.getLogger(__name__)

class UatVerifierAgentService:
    def __init__(self, poll_interval=30):
        self.poll_interval = poll_interval
        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.agent_username = "uat_verifier_agent"
        self.log_board_name = "UAT-Channel"
        self.agent_user = None
        self.log_board = None
        self.is_initialized = False
        self.bitsync_service = BitSyncService()
        self.sync_service = SyncService()

    def start(self):
        self.thread.start()
        logger.info("UAT Verifier Agent Service thread started.")

    def stop(self):
        self.shutdown_event.set()

    def _initialize_agent(self):
        try:
            self.agent_user, created = User.objects.get_or_create(
                username=self.agent_username,
                defaults={'is_agent': True, 'is_moderator': True, 'is_active': True}
            )
            if created:
                logger.info(f"Created UAT Verifier Agent user: {self.agent_username}")

            self.log_board, _ = MessageBoard.objects.get_or_create(name=self.log_board_name)
            self.is_initialized = True
            logger.info(f"UAT Verifier Agent '{self.agent_username}' initialized. Listening to board '{self.log_board_name}'.")
            return True
        except Exception as e:
            logger.warning(f"UAT Verifier Agent cannot initialize yet: {e}")
            return False

    def _run(self):
        time.sleep(20) # Wait for server to be fully ready
        while not self.shutdown_event.is_set():
            if not self.is_initialized:
                self._initialize_agent()
            
            if self.is_initialized:
                try:
                    self.process_uat_triggers()
                except Exception as e:
                    logger.error(f"Error in UAT Verifier Agent loop: {e}", exc_info=True)

            self.shutdown_event.wait(self.poll_interval)

    def process_uat_triggers(self):
        triggers = Message.objects.filter(
            board=self.log_board,
            subject__iexact="start_uat",
            agent_status='pending'
        ).exclude(author=self.agent_user)

        for trigger in triggers:
            try:
                logger.info(f"UAT Verifier Agent processing trigger message {trigger.id}")
                payload = json.loads(trigger.body)
                run_log = payload.get("run_log")
                uat_user_pubkey = payload.get("uat_user_pubkey")
                if not run_log or not uat_user_pubkey:
                    raise ValueError("Trigger message is missing run_log or uat_user_pubkey.")
                results = self.run_verification_suite(run_log, uat_user_pubkey)
                self.post_results(results)
                trigger.agent_status = 'processed'
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse UAT payload from trigger message {trigger.id}: {e}")
                trigger.agent_status = 'failed'
            except Exception as e:
                logger.error(f"Error processing UAT trigger {trigger.id}: {e}", exc_info=True)
                trigger.agent_status = 'failed'
            
            trigger.save()

    def run_verification_suite(self, run_log, uat_user_pubkey):
        results = []
        logger.info("--- UAT Verification Suite Started ---")
        
        time.sleep(60)

        results.append(self.verify_public_post(run_log))
        results.append(self.verify_attachment_federation(run_log))
        results.append(self.verify_private_message(run_log))
        results.append(self.verify_nickname_federation(run_log))

        logger.info("--- UAT: Auto-approving moderation items ---")
        results.append(self.auto_approve_report(run_log))
        results.append(self.auto_approve_profile_update(run_log))

        logger.info("--- UAT: Waiting for moderation actions to federate ---")
        time.sleep(60)

        results.append(self.verify_message_deletion_after_report(run_log))
        results.append(self.verify_avatar_federation(run_log))

        logger.info("--- UAT: Sending attachment back to host ---")
        results.append(self.send_attachment_to_host(run_log, uat_user_pubkey))

        logger.info("--- UAT Verification Suite Finished ---")
        return results

    def _get_log_entry(self, run_log, step_prefix):
        return next((item for item in run_log if item['step'].startswith(step_prefix)), None)

    def verify_public_post(self, run_log):
        log_entry = self._get_log_entry(run_log, "5)")
        if not (log_entry and log_entry['status'] == 'PASS'):
            return {"check": "Public Post Creation", "result": "FAIL", "details": "Prerequisite step did not pass on host."}
        subject = log_entry['details']['subject']
        if Message.objects.filter(subject=subject).exists():
            return {"check": "Public Post Creation", "result": "PASS"}
        else:
            return {"check": "Public Post Creation", "result": "FAIL", "details": f"Could not find message with subject '{subject}'."}

    def verify_attachment_federation(self, run_log):
        post_log_entry = self._get_log_entry(run_log, "5)")
        upload_log_entry = self._get_log_entry(run_log, "4)")
        if not (post_log_entry and upload_log_entry and upload_log_entry['status'] == 'PASS'):
            return {"check": "Attachment Federation", "result": "FAIL", "details": "Prerequisite step did not pass on host."}

        subject = post_log_entry['details']['subject']
        original_content = upload_log_entry['details']['content']
        try:
            message = Message.objects.get(subject=subject)
            if not message.attachments.exists():
                return {"check": "Attachment Federation", "result": "FAIL", "details": "Message was found, but its attachment has not federated yet."}
            attachment = message.attachments.first()
            decrypted_bytes = self.sync_service.get_decrypted_content(attachment.metadata_manifest)
            decrypted_payload = json.loads(decrypted_bytes.decode('utf-8'))
            retrieved_content = base64.b64decode(decrypted_payload.get('data')).decode('utf-8')
            if retrieved_content == original_content:
                return {"check": "Attachment Federation", "result": "PASS"}
            else:
                return {"check": "Attachment Federation", "result": "FAIL", "details": "Attachment content mismatch."}
        except Exception as e:
            return {"check": "Attachment Federation", "result": "FAIL", "details": str(e)}

    def verify_private_message(self, run_log):
        log_entry = self._get_log_entry(run_log, "6)")
        if not (log_entry and log_entry['status'] == 'PASS'):
            return {"check": "Private Message Federation", "result": "FAIL", "details": "Prerequisite step did not pass on host."}
        try:
            sender_pubkey = log_entry['details']['sender_pubkey']
            expected_sender_checksum = generate_checksum(sender_pubkey)
            recipient = User.objects.get(nickname__iexact="pibbs_user")
            expected_recipient_checksum = generate_checksum(recipient.pubkey)
            pm = PrivateMessage.objects.filter(recipient=recipient).order_by('-created_at').first()
            if not pm: return {"check": "Private Message Federation", "result": "FAIL", "details": "No PM received."}
            
            metadata = json.loads(self.sync_service.get_decrypted_content(pm.metadata_manifest).decode('utf-8'))
            if metadata.get('sender_pubkey_checksum') != expected_sender_checksum:
                return {"check": "Private Message Federation", "result": "FAIL", "details": "Sender checksum mismatch."}
            if metadata.get('recipient_pubkey_checksum') != expected_recipient_checksum:
                return {"check": "Private Message Federation", "result": "FAIL", "details": "Recipient checksum mismatch."}
            return {"check": "Private Message Federation", "result": "PASS"}
        except Exception as e:
            return {"check": "Private Message Federation", "result": "FAIL", "details": str(e)}

    def verify_nickname_federation(self, run_log):
        log_entry = self._get_log_entry(run_log, "8)")
        if not (log_entry and log_entry['status'] == 'PASS'):
            return {"check": "Nickname Federation", "result": "FAIL", "details": "Prerequisite step did not pass on host."}
        new_nickname = log_entry['details'].split("'")[1]
        if User.objects.filter(nickname__iexact=new_nickname, is_active=False).exists() or Alias.objects.filter(nickname__iexact=new_nickname).exists():
            return {"check": "Nickname Federation", "result": "PASS"}
        else:
            return {"check": "Nickname Federation", "result": "FAIL", "details": f"Could not find federated user/alias for '{new_nickname}'."}

    def auto_approve_report(self, run_log):
        log_entry = self._get_log_entry(run_log, "5)")
        subject = log_entry['details']['subject']
        try:
            message_to_delete = Message.objects.get(subject=subject)
            FederatedAction.objects.create(
                action_type='DELETE_CONTENT',
                content_hash_target=message_to_delete.metadata_manifest.get('content_hash'),
                action_details={'reason': f'Content auto-deleted by UAT verifier agent'}
            )
            message_to_delete.delete()
            return {"check": "Auto-Approve Message Report", "result": "PASS"}
        except Exception as e:
            return {"check": "Auto-Approve Message Report", "result": "FAIL", "details": str(e)}

    def auto_approve_profile_update(self, run_log):
        log_entry = self._get_log_entry(run_log, "3)")
        pubkey = log_entry['details']['pubkey']
        try:
            action = FederatedAction.objects.get(pubkey_target=pubkey, action_type='update_profile', status='pending_approval')
            user = User.objects.get(pubkey=action.pubkey_target)
            details = action.action_details
            temp_filename = details.get('pending_avatar_filename')

            if temp_filename:
                pending_dir = os.path.join(settings.MEDIA_ROOT, 'pending_avatars')
                source_path = os.path.join(pending_dir, temp_filename)
                final_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
                os.makedirs(final_dir, exist_ok=True)
                final_filename = f"{user.username}_avatar.png"
                final_path = os.path.join(final_dir, final_filename)
                os.rename(source_path, final_path)
                user.avatar.name = os.path.join('avatars', final_filename)
                with open(final_path, 'rb') as f:
                    image_bytes = f.read()
                file_content = {"type": "file", "filename": final_filename, "content_type": 'image/png', "size": len(image_bytes), "data": base64.b64encode(image_bytes).decode('ascii')}
                _content_hash, manifest = self.bitsync_service.create_encrypted_content(file_content)
                FileAttachment.objects.update_or_create(author=user, filename=final_filename, defaults={'content_type': 'image/png', 'size': len(image_bytes), 'manifest': manifest})
                details['avatar_hash'] = manifest.get('content_hash')

            user.nickname = details.get('nickname', user.nickname)
            user.save()
            action.status = 'approved'
            action.action_details = details
            action.save()
            return {"check": "Auto-Approve Profile Update", "result": "PASS"}
        except Exception as e:
            return {"check": "Auto-Approve Profile Update", "result": "FAIL", "details": str(e)}

    def verify_message_deletion_after_report(self, run_log):
        log_entry = self._get_log_entry(run_log, "5)")
        subject = log_entry['details']['subject']
        if not Message.objects.filter(subject=subject).exists():
            return {"check": "Message Deletion Verification", "result": "PASS"}
        else:
            return {"check": "Message Deletion Verification", "result": "FAIL", "details": "Message was not deleted."}

    def verify_avatar_federation(self, run_log):
        log_entry = self._get_log_entry(run_log, "3)")
        pubkey = log_entry['details']['pubkey']
        try:
            user = User.objects.get(pubkey=pubkey)
            if user.avatar and user.avatar.name:
                return {"check": "Avatar Federation Verification", "result": "PASS"}
            else:
                return {"check": "Avatar Federation Verification", "result": "FAIL", "details": "User avatar field is empty."}
        except User.DoesNotExist:
            return {"check": "Avatar Federation Verification", "result": "FAIL", "details": "User not found."}

    def post_results(self, results):
        final_status = "PASS" if all(r['result'] == "PASS" for r in results) else "FAIL"
        subject = f"UAT Results: {final_status}"
        body = f"UAT Verification Complete\nStatus: {final_status}\n\n"
        for res in results:
            body += f"- {res['check']:<35} [{res['result']}]\n"
            if res['result'] != "PASS":
                body += f"  Details: {res.get('details', 'N/A')}\n"

        content_to_encrypt = {"type": "message", "subject": subject, "body": body, "board": self.log_board.name, "pubkey": self.agent_user.pubkey}
        _content_hash, manifest = self.bitsync_service.create_encrypted_content(content_to_encrypt)
        Message.objects.create(board=self.log_board, author=self.agent_user, pubkey=self.agent_user.pubkey, subject=subject, body=body, metadata_manifest=manifest, agent_status='processed')
        logger.info(f"UAT Verifier Agent posted results: {final_status}")

    def send_attachment_to_host(self, run_log, uat_user_pubkey):
        log_entry = self._get_log_entry(run_log, "5)")
        if not (log_entry and log_entry['status'] == 'PASS'):
            return {"check": "Send Attachment to Host", "result": "FAIL", "details": "Prerequisite step did not pass on host."}
        
        original_message_subject = log_entry['details']['subject']
        original_message = Message.objects.filter(subject=original_message_subject).first()
        
        recipient_pubkey = uat_user_pubkey
        if not recipient_pubkey:
             return {"check": "Send Attachment to Host", "result": "FAIL", "details": "Original message has no public key."}
        
        subject = f"Re: {original_message_subject}"
        body = "This is a reply from the UAT verifier agent with an attachment."
        attachment_content = "This is the content of the attachment from the peer."
        attachment_filename = "peer_attachment.txt"

        try:
            self._create_and_send_reply(recipient_pubkey, subject, body, attachment_content, attachment_filename, parent_message=original_message)
            return {"check": "Send Attachment to Host", "result": "PASS"}
        except Exception as e:
            return {"check": "Send Attachment to Host", "result": "FAIL", "details": str(e)}

    def _create_and_send_reply(self, recipient_pubkey, subject, body, attachment_content, attachment_filename, parent_message=None):
        file_content_payload = {
            "type": "file",
            "filename": attachment_filename,
            "content_type": "text/plain",
            "size": len(attachment_content),
            "data": base64.b64encode(attachment_content.encode('utf-8')).decode('ascii')
        }
        _content_hash, manifest = self.bitsync_service.create_encrypted_content(file_content_payload)
        attachment = FileAttachment.objects.create(
            author=self.agent_user,
            filename=attachment_filename,
            content_type="text/plain",
            size=len(attachment_content),
            metadata_manifest=manifest
        )

        message_content = {
            "type": "message",
            "subject": subject,
            "body": body,
            "board": self.log_board.name,
            "pubkey": self.agent_user.pubkey,
            "attachment_hashes": [manifest.get('content_hash')]
        }
        _content_hash, message_manifest = self.bitsync_service.create_encrypted_content(message_content)
        message = Message.objects.create(
            board=self.log_board,
            author=self.agent_user,
            pubkey=self.agent_user.pubkey,
            subject=subject,
            body=body,
            metadata_manifest=message_manifest,
            parent=parent_message
        )
        message.attachments.set([attachment])
        message.save()
