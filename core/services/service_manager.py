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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/services/service_manager.py
import logging
import importlib
from django.db import connection
from .bitsync_service import BitSyncService
from .tor_service import TorService
from .sync_service import SyncService
from .high_score_service import HighScoreService

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.tor_service = TorService(host='127.0.0.1', port=9050)
        self.bitsync_service = None
        self.sync_service = None
        self.high_score_service = None
        self.game_agents = {} # Use a dict to track running agents by username

    def initialize_services(self):
        logger.info("Initializing Tor service...")
        # self.tor_service.start()

        logger.info("Initializing BitSync service...")
        self.bitsync_service = BitSyncService()
        
        logger.info("Initializing and starting SyncService thread...")
        self.sync_service = SyncService()
        self.sync_service.start()
        
        logger.info("Initializing and starting HighScoreService thread...")
        self.high_score_service = HighScoreService()
        self.high_score_service.start()

        self.start_game_agents()
        
        logger.info("All services initialized.")

    def start_game_agents(self):
        from core.models import User

        try:
            if User._meta.db_table not in connection.introspection.table_names():
                logger.warning("User table not yet created. Skipping agent initialization.")
                return
        except Exception as e:
            logger.error(f"Database connection not ready, skipping agent initialization: {e}")
            return

        agent_users = User.objects.filter(is_agent=True)
        if not agent_users.exists():
            logger.info("No game agents configured to run.")
            return

        logger.info(f"Found {agent_users.count()} game agent(s) to start...")
        for agent_user in agent_users:
            try:
                module_name = f"core.services.{agent_user.username}_service"
                class_name = ''.join(word.capitalize() for word in agent_user.username.split('_')) + 'Service'
                
                logger.info(f"Attempting to start agent: {class_name} from {module_name}")
                
                agent_module = importlib.import_module(module_name)
                AgentClass = getattr(agent_module, class_name)
                
                agent_instance = AgentClass()
                agent_instance.start()
                self.game_agents[agent_user.username] = agent_instance
                
                logger.info(f"Successfully started agent for user '{agent_user.username}'.")

            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to start agent for user '{agent_user.username}'. Could not find matching service module or class.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while starting agent for '{agent_user.username}': {e}", exc_info=True)

    def reload_agent(self, username):
        logger.info(f"Attempting to hot-reload agent '{username}'...")
        if username not in self.game_agents:
            logger.error(f"Cannot reload: Agent '{username}' is not currently running.")
            return False

        # 1. Stop the old agent thread
        old_agent_instance = self.game_agents.get(username)
        old_agent_instance.stop()
        old_agent_instance.thread.join(timeout=10)
        if old_agent_instance.thread.is_alive():
            logger.error(f"Failed to stop agent thread for '{username}' in time.")
            return False
        logger.info(f"Old agent thread for '{username}' has stopped.")

        # 2. Reload the module and start a new instance
        try:
            module_name = f"core.services.{username}_service"
            class_name = ''.join(word.capitalize() for word in username.split('_')) + 'Service'

            agent_module = importlib.import_module(module_name)
            importlib.reload(agent_module)
            
            AgentClass = getattr(agent_module, class_name)
            
            new_agent_instance = AgentClass()
            new_agent_instance.start()
            self.game_agents[username] = new_agent_instance
            
            logger.info(f"Successfully reloaded and started new agent for '{username}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to reload and start new agent for '{username}': {e}", exc_info=True)
            del self.game_agents[username]
            return False

    def shutdown(self):
        if self.tor_service and self.tor_service.is_running():
            logger.info("Shutting down Tor service...")
            self.tor_service.stop()

service_manager = ServiceManager()

