import requests
import json

# --- CONFIGURATION ---
# Replace this with your LAPTOP's Web UI .onion address
LAPTOP_ONION_URL = "http://irvgoajs5slszfroepj5fpit3lcxn5gxpeffim3shjstb6akbjuuzdid.onion"
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
