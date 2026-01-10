# Axon BBS - a modern, anonymous, federated bulletin board system.
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


# Full path: axon_bbs/test_onion_connection.py
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
# The .onion URL of the peer you are trying to connect to.
# This is now loaded securely from your .env file using your existing variable.
PEER_ONION_URL = os.getenv("TEST_BBS_ONION")

# The SOCKS proxy provided by the Tor service
PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
# ---------------------

def test_connection():
    """
    Attempts to connect to the specified .onion URL through the Tor proxy.
    """
    print(f"Attempting to connect to: {PEER_ONION_URL}")
    print("Using SOCKS proxy at 127.0.0.1:9050...")

    if not PEER_ONION_URL:
        print("\nERROR: TEST_BBS_ONION is not set in your .env file.")
        print("Please add the following line to your .env file:")
        print('TEST_BBS_ONION="http://your_actual_onion_address.onion"')
        return

    try:
        # We use the /api/sync/ endpoint as it's a good health check.
        # A timeout of 60 seconds is reasonable for Tor.
        target_url = f"{PEER_ONION_URL.strip('/')}/api/sync/"
        
        response = requests.get(target_url, proxies=PROXIES, timeout=60)

        print(f"\nSUCCESS: Connection was successful!")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body (first 100 chars): {response.text[:100]}")

    except requests.exceptions.RequestException as e:
        print(f"\nFAILURE: Could not connect to the onion service.")
        print(f"Error: {e}")
        print("\nPossible causes:")
        print("1. The Tor service is not running on your machine.")
        print("2. The peer's BBS server is offline.")
        print("3. The TEST_BBS_ONION address in your .env file is incorrect.")
        print("4. The Tor network is experiencing high latency (try again later).")

if __name__ == "__main__":
    test_connection()
