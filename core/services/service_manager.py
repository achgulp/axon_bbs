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


# Full path: axon_bbs/core/services/service_manager.py
import logging
import importlib
from django.db import connection
from .bitsync_service import BitSyncService
from .tor_service import TorService
from .sync_service import SyncService
from applets.high_score_service import HighScoreService

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.tor_service = TorService(host='127.0.0.1', port=9050)
        self.bitsync_service = None
        self.sync_service = None
        self.high_score_service = None
        self.game_agents = {}  # User-based agents (keyed by username)
        self.realtime_services = {}  # Board-based realtime services (keyed by board_id)

    def initialize_services(self):
        from core.models import TrustedInstance
        logger.info("Initializing Tor service...")
        # self.tor_service.start()

        logger.info("Initializing BitSync service...")
        self.bitsync_service = BitSyncService()
        
        if TrustedInstance.objects.filter(is_trusted_peer=False).exists():
            logger.info("Initializing and starting SyncService thread...")
            self.sync_service = SyncService()
            self.sync_service.start()
        else:
            logger.warning("No local instance found. SyncService will not be started.")

        logger.debug("Initializing and starting HighScoreService thread...")
        self.high_score_service = HighScoreService()
        self.high_score_service.start()

        self.start_all_game_agents()
        self.start_all_realtime_boards()

        logger.debug("All services initialized.")

    def _load_and_start_agent(self, agent_user):
        """
        Dynamically loads and starts an agent service based on the path
        defined in the user's agent_service_path field.
        """
        try:
            username = agent_user.username
            service_path = agent_user.agent_service_path

            if not service_path:
                logger.error(f"Cannot start agent for user '{username}': 'Agent Service Path' is not set in admin.")
                return False

            try:
                # Split the full path into module and class name
                # e.g., 'applets.chat_agent_service.ChatAgentService' ->
                # ('applets.chat_agent_service', 'ChatAgentService')
                module_name, class_name = service_path.rsplit('.', 1)
            except ValueError:
                logger.error(f"Invalid service path for agent '{username}': '{service_path}'. Path must be in the format 'app.module.ClassName'.")
                return False

            logger.debug(f"Attempting to start agent: {class_name} from {module_name} for user '{username}'")
            
            agent_module = importlib.import_module(module_name)
            AgentClass = getattr(agent_module, class_name)
            
            # Pass the agent's parameters to its constructor
            agent_instance = AgentClass(**agent_user.agent_parameters)

            agent_instance.start()
            self.game_agents[username] = agent_instance

            logger.debug(f"Successfully started agent for user '{username}'.")
            return True

        except (ImportError, AttributeError):
            logger.error(f"Failed to start agent for user '{agent_user.username}'. Could not find module '{module_name}' or class '{class_name}'.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while starting agent for '{agent_user.username}': {e}", exc_info=True)
        return False

    def start_all_game_agents(self):
        from core.models import User

        try:
            if User._meta.db_table not in connection.introspection.table_names():
                logger.warning("User table not yet created. Skipping agent initialization.")
                return
        except Exception as e:
            logger.error(f"Database connection not ready, skipping agent initialization: {e}")
            return

        agent_users = User.objects.filter(is_agent=True, is_active=True)

        if not agent_users.exists():
            logger.debug("No active game agents configured to run.")
            return

        logger.debug(f"Found {agent_users.count()} active game agent(s) to start...")
        for agent_user in agent_users:
            self._load_and_start_agent(agent_user)
            
    def start_agent(self, user):
        """Starts a new agent service that is not currently running."""
        if not user.is_agent or not user.is_active:
            logger.warning(f"Cannot start agent for '{user.username}': 'is_agent' or 'is_active' flag is false.")
            return False
        if user.username in self.game_agents:
            logger.warning(f"Cannot start agent for '{user.username}': Service is already running.")
            return False
        
        return self._load_and_start_agent(user)

    def stop_agent(self, username):
        """Stops a running agent service."""
        if username not in self.game_agents:
            logger.warning(f"Cannot stop agent for '{username}': Service is not running.")
            return False
        
        logger.info(f"Attempting to stop agent '{username}'...")
        agent_instance = self.game_agents.get(username)
        agent_instance.stop()
        agent_instance.thread.join(timeout=10)
        if agent_instance.thread.is_alive():
            logger.error(f"Failed to stop agent thread for '{username}' in time.")
            return False
        
        del self.game_agents[username]
        logger.info(f"Agent '{username}' stopped successfully.")
        return True

    def reload_agent(self, username):
        logger.info(f"Attempting to hot-reload agent '{username}'...")
        if username not in self.game_agents:
            logger.error(f"Cannot reload: Agent '{username}' is not currently running.")
            return False

        if self.stop_agent(username):
            from core.models import User
            try:
                user = User.objects.get(username=username)
                return self.start_agent(user)
            except User.DoesNotExist:
                logger.error(f"Cannot restart agent for '{username}': User not found.")
                return False
        return False

    def start_all_realtime_boards(self):
        """
        Start RealtimeMessageService for all MessageBoards with is_realtime=True.
        Called during service initialization.
        """
        from messaging.models import MessageBoard
        from core.agents.realtime_message_service import RealtimeMessageService

        try:
            if MessageBoard._meta.db_table not in connection.introspection.table_names():
                logger.warning("MessageBoard table not yet created. Skipping realtime board initialization.")
                return
        except Exception as e:
            logger.error(f"Database connection not ready, skipping realtime board initialization: {e}")
            return

        realtime_boards = MessageBoard.objects.filter(is_realtime=True)

        if not realtime_boards.exists():
            logger.debug("No real-time message boards configured.")
            return

        logger.debug(f"Found {realtime_boards.count()} real-time message board(s) to start...")
        for board in realtime_boards:
            try:
                service = RealtimeMessageService(
                    board_id=board.id,
                    poll_interval=board.local_poll_interval,
                    federation_interval=board.federation_poll_interval,
                    use_lan_federation=board.use_lan_federation
                )
                service.start()
                self.realtime_services[board.id] = service
                logger.debug(f"Started RealtimeMessageService for board '{board.name}' (id={board.id}) - local={board.local_poll_interval}s, federation={board.federation_poll_interval}s, lan={board.use_lan_federation}")
            except Exception as e:
                logger.error(f"Failed to start RealtimeMessageService for board '{board.name}': {e}", exc_info=True)

    def start_realtime_board(self, board_id):
        """Start a realtime service for a specific board (manual start)"""
        from messaging.models import MessageBoard
        from core.agents.realtime_message_service import RealtimeMessageService

        if board_id in self.realtime_services:
            logger.warning(f"RealtimeMessageService for board {board_id} is already running.")
            return False

        try:
            board = MessageBoard.objects.get(id=board_id)
            if not board.is_realtime:
                logger.error(f"Cannot start realtime service for board '{board.name}': is_realtime=False")
                return False

            service = RealtimeMessageService(
                board_id=board.id,
                poll_interval=board.local_poll_interval,
                federation_interval=board.federation_poll_interval,
                use_lan_federation=board.use_lan_federation
            )
            service.start()
            self.realtime_services[board.id] = service
            logger.info(f"Started RealtimeMessageService for board '{board.name}' (id={board.id}) - local={board.local_poll_interval}s, federation={board.federation_poll_interval}s, lan={board.use_lan_federation}")
            return True

        except MessageBoard.DoesNotExist:
            logger.error(f"Cannot start realtime service: MessageBoard {board_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to start RealtimeMessageService for board {board_id}: {e}", exc_info=True)
            return False

    def stop_realtime_board(self, board_id):
        """Stop a running realtime service for a specific board"""
        if board_id not in self.realtime_services:
            logger.warning(f"Cannot stop realtime service for board {board_id}: Not running.")
            return False

        logger.info(f"Stopping RealtimeMessageService for board {board_id}...")
        service = self.realtime_services.get(board_id)
        service.stop()  # This now handles both threads internally with join()

        # Check if threads stopped (stop() already does join with timeout)
        if service.local_thread.is_alive() or service.federation_thread.is_alive():
            logger.error(f"Failed to stop realtime service threads for board {board_id} in time.")
            return False

        del self.realtime_services[board_id]
        logger.info(f"RealtimeMessageService for board {board_id} stopped successfully.")
        return True

    def shutdown(self):
        if self.tor_service and self.tor_service.is_running():
            logger.info("Shutting down Tor service...")
            self.tor_service.stop()

service_manager = ServiceManager()
