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

# Full path: axon_bbs/core/management/commands/setup_realtime_test_board.py

from django.core.management.base import BaseCommand
from messaging.models import MessageBoard
from core.services.service_manager import service_manager

class Command(BaseCommand):
    help = """
    Creates a test real-time message board and starts its RealtimeMessageService.
    Usage: python manage.py setup_realtime_test_board [--room-id ROOM_ID] [--peers PEER1 PEER2 ...]
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--room-id',
            type=str,
            default='test-realtime-board',
            help='Federation room ID for the test board (default: test-realtime-board)'
        )
        parser.add_argument(
            '--peers',
            nargs='*',
            default=[],
            help='List of trusted peer onion URLs (e.g., http://peer1.onion http://peer2.onion)'
        )

    def handle(self, *args, **options):
        room_id = options['room_id']
        peers = options['peers']

        self.stdout.write(self.style.WARNING(f"\n=== Setting up Real-Time Test Board ==="))
        self.stdout.write(f"Room ID: {room_id}")
        self.stdout.write(f"Trusted Peers: {peers if peers else '(none - local only)'}\n")

        # Check if board already exists
        existing_board = MessageBoard.objects.filter(federation_room_id=room_id).first()
        if existing_board:
            self.stdout.write(self.style.WARNING(f"Board with room_id '{room_id}' already exists: {existing_board.name}"))
            self.stdout.write(self.style.WARNING(f"Updating configuration..."))

            board = existing_board
            board.is_realtime = True
            board.trusted_peers = peers
            board.message_retention_days = 1
            board.save()
        else:
            # Create new board
            board = MessageBoard.objects.create(
                name="Realtime Test Board",
                description="Test board for real-time federation with 1s latency. Messages expire after 1 day.",
                required_access_level=10,
                is_realtime=True,
                federation_room_id=room_id,
                trusted_peers=peers,
                message_retention_days=1
            )
            self.stdout.write(self.style.SUCCESS(f"Created new board: {board.name} (id={board.id})"))

        # Start the realtime service
        if board.id in service_manager.realtime_services:
            self.stdout.write(self.style.WARNING(f"RealtimeMessageService already running for board {board.id}"))
            self.stdout.write("Restarting service...")
            service_manager.stop_realtime_board(board.id)

        success = service_manager.start_realtime_board(board.id)

        if success:
            self.stdout.write(self.style.SUCCESS(f"\n✓ RealtimeMessageService started successfully!"))
            self.stdout.write(f"\nBoard Configuration:")
            self.stdout.write(f"  Name: {board.name}")
            self.stdout.write(f"  ID: {board.id}")
            self.stdout.write(f"  Room ID: {board.federation_room_id}")
            self.stdout.write(f"  Retention: {board.message_retention_days} day(s)")
            self.stdout.write(f"  Trusted Peers: {board.trusted_peers if board.trusted_peers else '(none)'}")

            self.stdout.write(f"\nEndpoints:")
            self.stdout.write(f"  SSE Stream: /api/realtime/boards/{board.id}/events/?tz=America/Detroit")
            self.stdout.write(f"  Federation API: /api/realtime/rooms/{board.federation_room_id}/messages/?since=<timestamp>")

            self.stdout.write(f"\nTest by posting a message:")
            self.stdout.write(f"  Go to /admin/messaging/messageboard/{board.id}/change/")
            self.stdout.write(f"  Or use the API: POST /api/messages/post/")
            self.stdout.write(f"    {{\"board_id\": {board.id}, \"subject\": \"Test\", \"body\": \"Hello realtime!\"}}")
        else:
            self.stdout.write(self.style.ERROR("\n✗ Failed to start RealtimeMessageService"))
            self.stdout.write("Check logs for details")
