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


# axon_bbs/minimal_test.py

import socks
import socket

print("Configuring SOCKS proxy with remote DNS...")
try:
    # --- CHANGE START ---
    # Hardcoded port 9999 changed to 9050, the standard Tor default.
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050, rdns=True)
    # --- CHANGE END ---
    socket.socket = socks.socksocket
    print("Proxy configured.")
except Exception as e:
    print(f"Failed to configure proxy: {e}")
    exit()

target_host = "relay.damus.io"
target_port = 443

print(f"\nAttempting to create a connection to {target_host}:{target_port}...")

try:
    # This command attempts a direct socket connection
    socket.create_connection((target_host, target_port), timeout=10)
    print("\nSUCCESS: Connection was successful!")
    print("This means PySocks and your proxy are working correctly.")
except Exception as e:
    print(f"\nFAILURE: Connection failed.")
    print(f"Error: {e}")
