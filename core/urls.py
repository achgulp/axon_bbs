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

# Full path: axon_bbs/core/urls.py

from django.urls import path
from core.views.applet_events import applet_event_stream, chat_event_stream
from core.views.realtime_board_events import realtime_board_events
from core.views.realtime_federation_api import RealtimeRoomMessagesView
from core.views.kairo_api import post_intent, cortex_events
from core.views.upload_api import upload_recording

urlpatterns = [
    # AxonChat SSE stream (new realtime implementation)
    path('chat/events/', chat_event_stream, name='chat_event_stream'),

    # Server-Sent Events (SSE) stream for real-time chat updates (legacy AxonChat - DEPRECATED)
    path('applets/<uuid:applet_id>/events/', applet_event_stream, name='applet_event_stream'),

    # Generic real-time message board SSE endpoint
    path('realtime/boards/<int:board_id>/events/', realtime_board_events, name='realtime_board_events'),

    # Federation API for real-time message boards
    path('realtime/rooms/<str:room_id>/messages/', RealtimeRoomMessagesView.as_view(), name='realtime_room_messages'),

    # KairoCortex API endpoints
    path('kairo/intent/', post_intent, name='kairo_post_intent'),
    path('kairo/events/', cortex_events, name='kairo_cortex_events'),
    
    # Recording Upload
    path('upload_recording/', upload_recording, name='upload_recording'),
]
