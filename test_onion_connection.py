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


# axon_bbs/test_onion_connection.py

import requests
import json

# --- CONFIGURATION ---
# --- CHANGE START ---
# The hardcoded .onion URL has been replaced with a placeholder.
LAPTOP_ONION_URL = "http://INSERT_YOUR_ONION_URL_HERE.onion"
# --- CHANGE END ---
# ---------------------

# This is the endpoint we are trying to reach
target_url = LAPTOP_ONION_URL.strip('/') + '/api/receive_magnet/'

# A dummy payload, similar to what the real app sends
payload = {
    'magnet': 'test',
    'signature': 'test',
    'sender_pubkey': 'test'
}

# The Tor SOCKS proxy
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

print(f"[*] Attempting to send a POST request to: {target_url}")
print("[*] Using Tor SOCKS proxy at 127.0.0.1:9050")

try:
    # We use a long timeout to account for Tor's latency
    response = requests.post(target_url, json=payload, proxies=proxies, timeout=120)

    print("\n[SUCCESS] The connection was successful!")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")

except requests.exceptions.RequestException as e:
    print("\n[FAILURE] The connection failed.")
    print(f"Error: {e}")
