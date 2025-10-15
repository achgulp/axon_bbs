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

# Full path: axon_bbs/core/views/applet_events.py

import json
import time
from django.http import StreamingHttpResponse
from core.models import AppletSharedState

def applet_event_stream(request, applet_id):
    """
    Handles the Server-Sent Events (SSE) stream for a given applet.
    This view keeps a connection open and pushes data to the client
    when the applet's shared state is updated.
    """
    def event_stream():
        # Get the last event ID from the client, if it exists. This allows
        # the client to "catch up" on missed messages if it disconnects.
        last_event_id_str = request.headers.get('Last-Event-ID')
        last_event_id = 0
        if last_event_id_str and last_event_id_str.isdigit():
            last_event_id = int(last_event_id_str)

        while True:
            # Query for any new state updates since the last one we sent.
            # This is more efficient than fetching the whole state.
            try:
                new_state = AppletSharedState.objects.filter(
                    applet_id=applet_id,
                    id__gt=last_event_id
                ).order_by('id').first()

                if new_state:
                    last_event_id = new_state.id
                    # Format the data in SSE message format.
                    # "id" is used for the Last-Event-ID header on reconnect.
                    # "data" is the JSON payload.
                    yield f"id: {new_state.id}\n"
                    yield f"data: {json.dumps(new_state.state_data)}\n\n"
                
                # Wait a short time before checking again to avoid
                # overwhelming the database (a busy-wait loop).
                time.sleep(1)
            
            except GeneratorExit:
                # This exception is raised when the client disconnects.
                # We can simply break the loop to clean up the connection.
                break

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache' # Ensure no proxy caches the stream
    response['X-Accel-Buffering'] = 'no' # Nginx-specific setting to disable buffering
    return response
