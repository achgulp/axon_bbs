# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY;
# without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/federation/moderator_agent_service.py
import threading
import time
import logging
import json
from django.utils import timezone
from datetime import timedelta

from core.models import User, TrustedInstance
from messaging.models import Message, MessageBoard
from federation.models import ModerationReport, FederatedAction
from accounts.models import BannedPubkey
from core.services.bitsync_service import BitSyncService

logger = logging.getLogger(__name__)

class ModeratorAgentService:
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval
        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.agent_username = "moderator_agent"
        self.log_board_name = "Moderation"
        self.agent_user = None
        self.log_board = None
        self.is_initialized = False
        self.bitsync_service = BitSyncService()
        self.host_pubkey = None

    def start(self):
        self.thread.start()
        logger.info("Moderator Agent Service thread started.")

    def stop(self):
        self.shutdown_event.set()

    def _initialize_agent(self):
        try:
            self.agent_user = User.objects.get(username=self.agent_username, is_agent=True)
            self.log_board, _ = MessageBoard.objects.get_or_create(name=self.log_board_name)
            
            local_instance = TrustedInstance.objects.filter(is_trusted_peer=False).first()
            if local_instance:
                self.host_pubkey = local_instance.pubkey

            self.is_initialized = True
            logger.info(f"Moderator Agent '{self.agent_username}' initialized. Logging to board '{self.log_board_name}'.")
            return True
        except (User.DoesNotExist, TrustedInstance.DoesNotExist) as e:
            logger.warning(f"Moderator Agent cannot initialize yet: {e}")
            return False

    def _run(self):
        time.sleep(15) # Wait for server to be fully ready
        while not self.shutdown_event.is_set():
            if not self.is_initialized:
                self._initialize_agent()
            
            if self.is_initialized:
                try:
                    self.process_completed_reports()
                    self.process_federated_actions()
                    self.process_incoming_logs()
                except Exception as e:
                    logger.error(f"Error in Moderator Agent loop: {e}", exc_info=True)

            self.shutdown_event.wait(self.poll_interval)

    def process_incoming_logs(self):
        """Reads the moderation board for events from other agents and applies them locally."""
        incoming_logs = Message.objects.filter(
            board=self.log_board,
            agent_status='pending'
        ).exclude(author=self.agent_user)

        for log_message in incoming_logs:
            try:
                log_data = json.loads(log_message.body)
                details = log_data.get('details', {})
                
                if log_data.get('log_type') == 'FEDERATED_ACTION':
                    action_type = details.get('action_type')
                    
                    if action_type == 'ban_pubkey':
                        pubkey = details.get('target_pubkey')
                        if pubkey:
                            action_details = details.get('action_details', {})
                            is_temporary = action_details.get('is_temporary', False)
                            duration = action_details.get('duration_hours')
                            expires_at = None
                            
                            if is_temporary and duration:
                                expires_at = timezone.now() + timedelta(hours=int(duration))
                            
                            BannedPubkey.objects.update_or_create(
                                pubkey=pubkey,
                                defaults={'is_temporary': is_temporary, 'expires_at': expires_at}
                            )
                            logger.info(f"Applied federated ban for pubkey: {pubkey[:12]}...")

                    elif action_type == 'DELETE_CONTENT':
                        content_hash = details.get('target_hash')
                        if content_hash:
                            Message.objects.filter(metadata_manifest__content_hash=content_hash).delete()
                            logger.info(f"Applied federated delete for content hash: {content_hash[:12]}...")

                log_message.agent_status = 'processed'
            except json.JSONDecodeError:
                logger.warning(f"Moderator agent could not parse incoming log message body (ID: {log_message.id})")
                log_message.agent_status = 'failed'
            except Exception as e:
                logger.error(f"Error processing incoming log (ID: {log_message.id}): {e}", exc_info=True)
                log_message.agent_status = 'failed'
            
            log_message.save()

    def process_completed_reports(self):
        """Finds local moderation reports that have been approved/rejected and logs them."""
        reports_to_log = ModerationReport.objects.filter(is_logged=False).exclude(status='pending')
        for report in reports_to_log:
            moderator = report.reviewed_by
            
            timestamp_to_log = report.reviewed_at if report.reviewed_at else timezone.now()
            
            log_entry = {
                "log_type": "REPORT_REVIEWED",
                "moderator_nickname": moderator.nickname if moderator else "System",
                "moderator_bbs_pubkey": self.host_pubkey,
                "timestamp": timestamp_to_log.isoformat(),
                "details": {
                    "report_id": report.id,
                    "reporter_nickname": report.reporting_user.nickname,
                    "decision": report.status,
                    "target_message_subject": report.reported_message.subject if report.reported_message else "[Message Deleted]",
                    "target_message_hash": report.reported_message.metadata_manifest.get('content_hash') if report.reported_message and report.reported_message.metadata_manifest else "N/A"
                }
            }
            self._post_log_entry(f"Report Reviewed: {report.id}", log_entry)
            report.is_logged = True
            report.save()

    def process_federated_actions(self):
        """Finds local federated actions (like bans) and logs them."""
        actions_to_log = FederatedAction.objects.filter(is_logged=False, status='approved', created_at__isnull=False)
        for action in actions_to_log:
            log_entry = {
                "log_type": "FEDERATED_ACTION",
                "moderator_bbs_pubkey": self.host_pubkey,
                "timestamp": action.created_at.isoformat(),
                "details": {
                    "action_id": str(action.id),
                    "action_type": action.action_type,
                    "target_pubkey": action.pubkey_target,
                    "target_hash": action.content_hash_target,
                    "action_details": action.action_details
                }
            }
            self._post_log_entry(f"Federated Action: {action.action_type}", log_entry)
            action.is_logged = True
            action.save()

    def _post_log_entry(self, subject, body_data):
        if not self.agent_user or not self.log_board:
            return

        body_json = json.dumps(body_data, indent=2)
        content_to_encrypt = {
            "type": "message",
            "subject": subject,
            "body": body_json,
            "board": self.log_board.name,
            "pubkey": self.agent_user.pubkey
        }
        
        _content_hash, manifest = self.bitsync_service.create_encrypted_content(content_to_encrypt)

        Message.objects.create(
            board=self.log_board,
            author=self.agent_user,
            pubkey=self.agent_user.pubkey,
            subject=subject,
            body=body_json,
            metadata_manifest=manifest,
            agent_status='processed'
        )
        logger.info(f"Moderator Agent logged event: {subject}")
