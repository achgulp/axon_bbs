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


# Full path: axon_bbs/core/services/moderator_agent_service.py
import threading
import time
import logging
import json
from django.utils import timezone

from core.models import User, Message, MessageBoard, ModerationReport, FederatedAction, TrustedInstance
from .service_manager import service_manager
from .bitsync_service import BitSyncService

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
        # Store the host's public key once on initialization
        self.host_pubkey = None

    def start(self):
        self.thread.start()
        logger.info("Moderator Agent Service thread started.")

    def stop(self):
        self.shutdown_event.set()

    def _initialize_agent(self):
        try:
            self.agent_user = User.objects.get(username=self.agent_username, is_agent=True)
            self.log_board = MessageBoard.objects.get(name=self.log_board_name)
            
            local_instance = TrustedInstance.objects.filter(is_trusted_peer=False).first()
            if local_instance:
                self.host_pubkey = local_instance.pubkey

            self.is_initialized = True
            logger.info(f"Moderator Agent '{self.agent_username}' initialized. Logging to board '{self.log_board_name}'.")
            return True
        except (User.DoesNotExist, MessageBoard.DoesNotExist, TrustedInstance.DoesNotExist) as e:
            logger.warning(f"Moderator Agent cannot initialize yet: {e}")
            return False

    def _run(self):
        time.sleep(15) # Wait for Django to fully start
        while not self.shutdown_event.is_set():
            if not self.is_initialized:
                self._initialize_agent()
            
            if self.is_initialized:
                try:
                    self.process_completed_reports()
                    self.process_federated_actions()
                except Exception as e:
                    logger.error(f"Error in Moderator Agent loop: {e}", exc_info=True)

            self.shutdown_event.wait(self.poll_interval)

    def process_completed_reports(self):
        reports_to_log = ModerationReport.objects.filter(is_logged=False).exclude(status='pending')
        for report in reports_to_log:
            moderator = report.reviewed_by
            log_entry = {
                "log_type": "REPORT_REVIEWED",
                "moderator_nickname": moderator.nickname if moderator else "System",
                "moderator_bbs_pubkey": self.host_pubkey,
                "timestamp": report.reviewed_at.isoformat(),
                "details": {
                    "report_id": report.id,
                    "reporter_nickname": report.reporting_user.nickname,
                    "decision": report.status, # 'approved' or 'rejected'
                    "target_message_subject": report.reported_message.subject,
                    "target_message_hash": report.reported_message.manifest.get('content_hash')
                }
            }
            self._post_log_entry(f"Report Reviewed: {report.id}", log_entry)
            report.is_logged = True
            report.save()

    def process_federated_actions(self):
        actions_to_log = FederatedAction.objects.filter(is_logged=False, status='approved')
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
            manifest=manifest
        )
        logger.info(f"Moderator Agent logged event: {subject}")
