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


# Full path: axon_bbs/applets/overlord_agent_service.py
import threading
import time
import logging
import json
import random
import requests
import uuid
import math
from django.db import transaction
from django.db.models import Q
from messaging.models import Message
from applets.models import Applet, AppletData, AppletSharedState
from core.models import User, TrustedInstance
from core.services.service_manager import service_manager
from core.services.bitsync_service import BitSyncService

logger = logging.getLogger(__name__)

# --- GAME CONFIGURATION ---
GAME_CONFIG = {
    "pvp_enabled": False,
    "buildings": {
        "Greenhouse": {"name": "Greenhouse", "cost": {"crystals": 75, "alloy": 25}, "build_time": 3},
        "Crystal Mine": {"name": "Crystal Mine", "cost": {"crystals": 100, "alloy": 0}, "build_time": 2},
        "Forge/Smelter": {"name": "Forge/Smelter", "cost": {"crystals": 150, "alloy": 50}, "build_time": 4, "consumes": {"rawOre": 5}, "produces": {"crystals": 2}},
        "Command Center": {"comm_range": 200},
    },
    "drones": {
        "Scout": {"cargo_capacity": 20, "harvest_rate": 5, "speed": 20} # Speed in units per tick
    },
    "world_tick": {
        "interval_seconds": 30,
        "npc_marauder_chance": 0.15
    }
}

class OverlordAgentService:
    def __init__(self, poll_interval=15, reconciliation_interval=300):
        self.poll_interval = poll_interval
        self.reconciliation_interval = reconciliation_interval
        self.world_tick_interval = GAME_CONFIG["world_tick"]["interval_seconds"]
        self.shutdown_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.last_reconciliation_time = 0
        self.last_world_tick_time = 0
        self.game_applet_name = "Fortress Overlord"
        self.agent_username = "overlord_agent" 
        self.agent_user = None
        self.game_board = None
        self.game_applet = None
        self.is_initialized = False
        self.bitsync_service = BitSyncService()
        self.sync_service = service_manager.sync_service

    def start(self):
        self.thread.start()
        logger.info("Overlord Agent Service thread started.")

    def stop(self):
        logger.info(f"Stopping agent service for {self.agent_username}...")
        self.shutdown_event.set()

    def _initialize_agent(self):
        try:
            self.agent_user = User.objects.get(username=self.agent_username, is_agent=True)
            self.game_applet = Applet.objects.get(name=self.game_applet_name)
            self.game_board = self.game_applet.event_board
            if not self.game_board:
                logger.warning(f"Agent '{self.agent_username}' cannot initialize: Game board not set for applet '{self.game_applet_name}'.")
                return False
            logger.info(f"Agent '{self.agent_user.username}' is monitoring board '{self.game_board.name}'.")
            self.is_initialized = True
            return True
        except (User.DoesNotExist, Applet.DoesNotExist):
            logger.warning(f"Agent '{self.agent_username}' cannot initialize yet: User or Applet not found in database.")
            return False

    def _run(self):
        time.sleep(10)

        while not self.shutdown_event.is_set():
            try:
                if not self.is_initialized:
                    if not self._initialize_agent():
                        self.shutdown_event.wait(self.poll_interval)
                        continue

                current_time = time.time()
                self.process_game_events()
                if current_time - self.last_world_tick_time > self.world_tick_interval:
                    self.perform_world_tick()
                    self.last_world_tick_time = current_time
            except Exception as e:
                logger.error(f"Error in Overlord agent loop: {e}", exc_info=True)
            
            self.shutdown_event.wait(self.poll_interval)
        
        logger.info(f"Agent service for {self.agent_username} has shut down gracefully.")

    def process_game_events(self):
        action_posts = Message.objects.filter(board=self.game_board, agent_status='pending').order_by('created_at')
        if not action_posts.exists(): return
        
        for post in action_posts:
            author = post.author
            player_data = self._get_player_data(author) if author else None
            if not player_data:
                post.agent_status = 'failed'
                post.save()
                continue

            try:
                try:
                    body = json.loads(post.body)
                except json.JSONDecodeError:
                    logger.warning(f"Agent skipping non-JSON message (ID: {post.id}) with subject '{post.subject}'.")
                    post.agent_status = 'processed' 
                    post.save()
                    continue
                
                command = post.subject.upper()
                drone_id = body.get('droneId')
                drone = next((d for d in player_data.get('drones', []) if d.get('id') == drone_id), None)

                if drone and not drone.get('is_in_comms_range', True):
                    self._post_agent_event("CMD_FAILED", {"summary": f"Cannot issue new command to {drone_id}: Drone is out of communication range."})
                    post.agent_status = 'processed'
                    post.save()
                    continue

                if command == "BUILD": self.handle_build(author, player_data, body)
                elif command == "ASSIGN_TASK": self.handle_assign_task(author, player_data, body)
                elif command == "CANCEL_TASK": self.handle_cancel_task(author, player_data, body)
                elif command == "STOP_TASK": self.handle_stop_task(author, player_data, body)
                
                post.agent_status = 'processed'
            except Exception as e:
                logger.error(f"Error processing event '{post.subject}': {e}", exc_info=True)
                post.agent_status = 'failed'
            
            post.save()

    def handle_build(self, author, player_data, body):
        building_type = body.get('buildingType')
        coords = body.get('coords')
        if not building_type or not coords:
            return

        build_info = GAME_CONFIG['buildings'].get(building_type)
        if not build_info:
            return

        player_resources = player_data.get('resources', {})
        can_afford = True
        for resource, cost in build_info['cost'].items():
            if player_resources.get(resource, 0) < cost:
                can_afford = False
                break
        
        if not can_afford:
            self._post_agent_event("BUILD_FAILED", {"summary": f"Insufficient resources for {building_type}."})
            return

        for resource, cost in build_info['cost'].items():
            player_resources[resource] -= cost
        
        new_building = {
            "id": f"bldg_{uuid.uuid4().hex[:6]}",
            "type": f"{building_type} (Construction Site)",
            "x": coords['x'],
            "y": coords['y'],
            "health": 10,
            "build_progress": 0,
            "build_total": build_info['build_time']
        }
        player_data.setdefault('buildings', []).append(new_building)
        
        self._save_player_data(author, player_data)
        self._post_agent_event("BUILD_STARTED", {"summary": f"Construction of {building_type} started at ({coords['x']}, {coords['y']})."})

    def handle_assign_task(self, author, player_data, body):
        pass
        
    def handle_cancel_task(self, author, player_data, body):
        pass

    def handle_stop_task(self, author, player_data, body):
        drone_id = body.get('droneId')
        drone = next((d for d in player_data.get('drones', []) if d.get('id') == drone_id), None)
        if not drone: return
        self.handle_cancel_task(author, player_data, body)
        self._post_agent_event("TASK_HALTED", {"summary": f"Drone {drone_id} has ceased current operations."})

    def set_drone_travel_task(self, drone, target, next_status):
        pass

    def set_drone_idle(self, drone):
        pass

    def perform_world_tick(self):
        all_players = User.objects.filter(is_agent=False, applet_data__applet=self.game_applet).distinct()
        for player in all_players:
            player_data = self._get_player_data(player)
            if not player_data: continue

            command_center = next((b for b in player_data.get('buildings', []) if b.get('type') == 'Command Center'), {'x': 0, 'y': 0})
            comm_range = GAME_CONFIG['buildings']['Command Center']['comm_range']
            
            for drone in player_data.get('drones', []):
                dist_to_base = math.sqrt((drone['x'] - command_center['x'])**2 + (drone['y'] - command_center['y'])**2)
                
                was_in_range = drone.get('is_in_comms_range', True)
                is_in_range = dist_to_base <= comm_range
                drone['is_in_comms_range'] = is_in_range

                if not was_in_range and is_in_range:
                    for event in drone.get('event_buffer', []):
                        self._post_agent_event(event['subject'], event['body'])
                    drone['event_buffer'] = []
                
                self.process_drone_tick(drone, player_data)
            
            self.process_construction(player_data)
            self.process_building_production(player_data)
            self._save_player_data(player, player_data)
            
    def process_drone_tick(self, drone, player_data):
        pass
    
    def process_construction(self, player_data):
        buildings_to_complete = []
        for building in player_data.get('buildings', []):
            if " (Construction Site)" in building.get('type', ''):
                building['build_progress'] += 1
                if building['build_progress'] >= building.get('build_total', 99):
                    buildings_to_complete.append(building)
        
        for b in buildings_to_complete:
            original_type = b['type'].replace(" (Construction Site)", "")
            b['type'] = original_type
            b['health'] = 1000
            del b['build_progress']
            del b['build_total']
            
            replay_data = {
                "eventType": "CONSTRUCTION_COMPLETE",
                "buildingType": original_type,
                "location": { "x": b['x'], "y": b['y'] },
                "duration": 8000
            }
            
            self._post_agent_event(
                "CONSTRUCTION_COMPLETE", 
                {
                    "summary": f"Fortress expansion complete: {original_type} is now operational.",
                    "replayData": replay_data
                }
            )

    def process_building_production(self, player_data):
        pass

    def _get_player_data(self, user):
        try:
            player_applet_data = AppletData.objects.get(applet=self.game_applet, owner=user)
            decrypted_bytes = self.sync_service.get_decrypted_content(player_applet_data.data_manifest)
            return json.loads(decrypted_bytes.decode('utf-8')).get('data', {}) if decrypted_bytes else None
        except AppletData.DoesNotExist:
            return None

    def _save_player_data(self, user, new_data):
        try:
            content_to_encrypt = {
                "type": "applet_data", "applet_id": str(self.game_applet.id),
                "owner_pubkey": user.pubkey, "data": new_data
            }
            _content_hash, manifest = self.bitsync_service.create_encrypted_content(content_to_encrypt, recipients_pubkeys=[user.pubkey])
            AppletData.objects.update_or_create(applet=self.game_applet, owner=user, defaults={'data_manifest': manifest})
        except Exception as e:
            logger.error(f"Failed to save data for user '{user.username}': {e}", exc_info=True)

    def _post_agent_event(self, subject, body_data):
        try:
            content_to_encrypt = {
                "type": "message", "subject": subject, "body": json.dumps(body_data),
                "board": self.game_board.name, "pubkey": self.agent_user.pubkey,
            }
            _content_hash, manifest = self.bitsync_service.create_encrypted_content(content_to_encrypt)
            Message.objects.create(
                board=self.game_board, subject=subject, body=content_to_encrypt['body'],
                author=self.agent_user, pubkey=self.agent_user.pubkey, manifest=manifest, agent_status='processed'
            )
        except Exception as e:
            logger.error(f"Agent failed to post event '{subject}': {e}")
