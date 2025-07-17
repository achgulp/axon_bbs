# axon_bbs/final_nostr_publish.py

import asyncio
import json
from websockets.legacy.client import connect
from python_socks.async_.asyncio import Proxy

# Use the already-installed pynostr library for crypto and event formatting
from pynostr.key import PrivateKey
from pynostr.event import Event

# --- Configuration ---
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 9999
RELAY_URI = 'wss://relay.damus.io'
NOTE_CONTENT = "Hello Nostr! This message was sent using the correct hybrid method."

async def main():
    # 1. Create keys and event using pynostr (already installed)
    private_key = PrivateKey()
    print(f"Using new private key: {private_key.bech32()}")
    event = Event(content=NOTE_CONTENT)
    event.sign(private_key.hex()) # pynostr handles all the complex signing logic

    # 2. Connect to the relay through the SOCKS proxy (our working method)
    print(f"\nConnecting to {RELAY_URI} via proxy...")
    proxy = Proxy.from_url(f'socks5://{PROXY_HOST}:{PROXY_PORT}')
    sock = await proxy.connect(dest_host=RELAY_URI.split('//')[1], dest_port=443)

    # 3. Establish the WebSocket connection and publish the event
    try:
        async with connect(
            RELAY_URI,
            sock=sock,
            server_hostname=RELAY_URI.split('//')[1]
        ) as websocket:
            print("Connection successful!")
            # pynostr has a method to format the event for publishing
            message = json.dumps(["EVENT", event.to_dict()])
            print(f"Sending event...")
            await websocket.send(message)
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            print(f"Received response from relay: {response}")
            return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    if asyncio.run(main()):
        print("\nSUCCESS: Nostr event published.")
    else:
        print("\nFAILURE: Could not publish Nostr event.")
