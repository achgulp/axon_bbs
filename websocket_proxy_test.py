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


# axon_bbs/websocket_proxy_test.py

import asyncio
from python_socks.async_.asyncio import Proxy
import websockets

# Proxy and target details
PROXY_HOST = '127.0.0.1'
# --- CHANGE START ---
# Hardcoded port 9999 changed to 9050, the standard Tor default.
PROXY_PORT = 9050
# --- CHANGE END ---
TARGET_URI = 'wss://relay.damus.io'

async def main():
    print(f"Connecting to proxy at {PROXY_HOST}:{PROXY_PORT}...")
    proxy = Proxy.from_url(f'socks5://{PROXY_HOST}:{PROXY_PORT}')

    sock = await proxy.connect(dest_host=TARGET_URI.split('//')[1], dest_port=443)
    print("Proxy connection successful.")

    print(f"Attempting WebSocket handshake with {TARGET_URI}...")
    try:
        async with websockets.connect(
            TARGET_URI,
            sock=sock,
            server_hostname=TARGET_URI.split('//')[1] # Important for TLS
        ) as websocket:

            print("WebSocket connection successful!")

            # Correct way to send a ping and wait for the pong
            print("Sending a ping and waiting for pong...")
            await websocket.ping()
            print("Pong received!")

            return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    if asyncio.run(main()):
        print("\nSUCCESS: A proxied WebSocket connection was established.")
    else:
        print("\nFAILURE: Could not establish a proxied WebSocket connection.")
