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


# axon_bbs/handlers/meshtastic_handler.py

import os
import sys
import django
import time
import meshtastic
import meshtastic.serial_interface

# -----------------------------------------------------------------------------
# Django Environment Setup
# -----------------------------------------------------------------------------
def setup_django_env():
    """
    Initializes the Django environment so this standalone script can access
    the Django models and services from the main project.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
    django.setup()
    print("Django environment initialized successfully.")

# -----------------------------------------------------------------------------
# Meshtastic Command Processor
# -----------------------------------------------------------------------------

class CommandProcessor:
    """
    Processes commands received from the Meshtastic network.
    """
    def __init__(self, mesh_interface):
        self.interface = mesh_interface
        # Import core models after Django is set up
        from core.models import User, Message, MessageBoard
        self.User = User
        self.Message = Message
        self.MessageBoard = MessageBoard

    def process_packet(self, packet, interface):
        """
        This is the callback function that gets called for each received packet.
        """
        if packet.get('decoded') and packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
            sender_id = packet['fromId']
            message_text = packet['decoded']['text']

            print(f"Received from {sender_id}: '{message_text}'")

            # Simple command parsing: !bbs <command> <args>
            if message_text.lower().startswith('!bbs '):
                parts = message_text.split(' ', 3)
                if len(parts) >= 2:
                    command = parts[1].lower()
                    
                    # --- Authenticate User ---
                    # In a real system, you'd map sender_id to a BBS user.
                    # For now, we'll use a hardcoded test user.
                    try:
                        user = self.User.objects.get(username='meshtastic_user')
                    except self.User.DoesNotExist:
                        self.send_reply("Error: 'meshtastic_user' not found in BBS.", sender_id)
                        return

                    # --- Process Commands ---
                    if command == 'post' and len(parts) == 4:
                        board_name = parts[2]
                        post_content = parts[3]
                        self.handle_post(user, board_name, post_content, sender_id)
                    elif command == 'boards':
                        self.handle_list_boards(user, sender_id)
                    else:
                        self.send_reply(f"Unknown command: '{command}'", sender_id)
                else:
                    self.send_reply("Invalid command format. Use: !bbs <command> [args]", sender_id)

    def handle_post(self, user, board_name, content, reply_to_id):
        """Handles posting a message to a board."""
        try:
            board = self.MessageBoard.objects.get(name__iexact=board_name)
            if user.sl >= board.required_sl:
                # Create the message in the BBS database
                Message.objects.create(
                    board=board,
                    author=user,
                    title=f"Post from {user.username}",
                    body=content
                )
                self.send_reply(f"Message posted to '{board.name}'.", reply_to_id)
            else:
                self.send_reply(f"Access denied to board '{board.name}'.", reply_to_id)
        except self.MessageBoard.DoesNotExist:
            self.send_reply(f"Error: Board '{board_name}' not found.", reply_to_id)

    def handle_list_boards(self, user, reply_to_id):
        """Handles listing available message boards."""
        boards = self.MessageBoard.objects.filter(required_sl__lte=user.sl)
        if boards:
            board_list = ", ".join([b.name for b in boards])
            self.send_reply(f"Boards: {board_list}", reply_to_id)
        else:
            self.send_reply("No accessible boards found.", reply_to_id)

    def send_reply(self, text, destination_id):
        """Sends a reply back to the user over the mesh."""
        print(f"Replying to {destination_id}: {text}")
        self.interface.sendText(text, destinationId=destination_id)

# -----------------------------------------------------------------------------
# Main Execution Block
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting Axon BBS Meshtastic Handler...")
    setup_django_env()

    try:
        # Initialize the connection to the Meshtastic device
        interface = meshtastic.serial_interface.SerialInterface()
        print("Connected to Meshtastic device.")
        
        # Instantiate the command processor
        processor = CommandProcessor(interface)

        # Register the callback function
        meshtastic.pub.subscribe(processor.process_packet, "meshtastic.receive")
        
        print("Listening for messages... Press Ctrl+C to exit.")
        while True:
            time.sleep(1)

    except meshtastic.MeshtasticException as e:
        print(f"Meshtastic error: {e}")
        print("Could not connect to Meshtastic device. Is it plugged in?")
    except KeyboardInterrupt:
        print("\nShutting down handler.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'interface' in locals() and interface:
            interface.close()


