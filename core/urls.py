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
from .views import (
    applet_state,
    applet_update,
    applet_events # Import the new view
)

urlpatterns = [
    # ... other existing url patterns ...

    # Endpoint for an applet to get its current shared state (still useful for initial load)
    path('api/applets/<int:applet_id>/state/', applet_state.get_applet_state, name='get_applet_state'),
    
    # Endpoint for an applet to post an update to its shared state
    path('api/applets/<int:applet_id>/update_state/', applet_update.update_applet_state, name='update_applet_state'),
    
    # NEW: Endpoint for the Server-Sent Events (SSE) stream
    path('api/applets/<int:applet_id>/events/', applet_events.applet_event_stream, name='applet_event_stream'),
]
