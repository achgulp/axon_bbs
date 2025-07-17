# axon_bbs/nostr_subscribe_and_publish.py

import asyncio
import json
import uuid
from websockets.legacy.client import connect
from python_socks.async_.asyncio import Proxy

# Use the already-installed pynostr library for crypto and event formatting
from pynostr.key import PrivateKey
from pynostr.event import Event

# --- Configuration ---
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 9050 # Changed to 9050 to connect to the local Tor service
RELAY_URI = 'wss://relay.damus.io'
NOTE_CONTENT = "Hello Nostr! This message is sent from Python -> Tor -> SOCKS Proxy."

async def listen_for_events(websocket):
    """
    A task that runs in the background, continuously listening for messages
    from the relay and printing them.
    """
    async for message in websocket:
        try:
            data = json.loads(message)
            msg_type = data[0]
            if msg_type == "EVENT":
                sub_id = data[1]
                event_id = data[2].get('id', 'N/A')
                content = data[2].get('content', '')
                print(f"\n<-- [EVENT] received on sub '{sub_id}':")
                print(f"    Content: {content[:100]}...")
                print(f"    Event ID: {event_id}")

            elif msg_type == "OK":
                event_id = data[1]
                was_accepted = data[2]
                print(f"\n<-- [OK] relay confirmation for event {event_id}. Accepted: {was_accepted}")

            elif msg_type == "EOSE":
                sub_id = data[1]
                print(f"\n<-- [EOSE] End of Stored Events for sub '{sub_id}'.")

        except Exception as e:
            print(f"Error processing message: {e}")


async def main():
    # 1. Create Nostr keys
    private_key = PrivateKey()
    print(f"Using new private key: {private_key.bech32()}")

    # 2. Connect to the relay through your local Tor SOCKS proxy
    print(f"\nConnecting to {RELAY_URI} via local Tor proxy (port 9050)...")
    proxy = Proxy.from_url(f'socks5://{PROXY_HOST}:{PROXY_PORT}')
    sock = await proxy.connect(dest_host=RELAY_URI.split('//')[1], dest_port=443)

    try:
        async with connect(RELAY_URI, sock=sock, server_hostname=RELAY_URI.split('//')[1]) as websocket:
            print("\nConnection successful! Python -> Tor -> SOCKS proxy chain is active.")

            # Start the background task to listen for all incoming messages
            listener_task = asyncio.create_task(listen_for_events(websocket))

            # 3. Subscribe to the 'general' channel
            general_sub_id = "general-feed"
            general_filter = {"kinds": [1], "limit": 5}
            await websocket.send(json.dumps(["REQ", general_sub_id, general_filter]))
            print(f"\n--> [REQ] Sent subscription for general channel.")
            await asyncio.sleep(3)

            # 4. Create and publish our own event
            print("\n----------------------------------------------------")
            print("Now, publishing our own event...")
            event = Event(content=NOTE_CONTENT)
            event.sign(private_key.hex())
            await websocket.send(json.dumps(["EVENT", event.to_dict()]))
            print(f"--> [EVENT] Sent our new note with ID: {event.id}")
            print("----------------------------------------------------")
            await asyncio.sleep(3)

            # 5. Re-pull our specific event by its ID
            repull_sub_id = "repull-our-note"
            repull_filter = {"ids": [event.id]}
            await websocket.send(json.dumps(["REQ", repull_sub_id, repull_filter]))
            print(f"\n--> [REQ] Sent new subscription to re-pull our specific event.")
            await asyncio.sleep(10)

            # 7. Clean up
            listener_task.cancel()
            print("\nDone listening. Closing connection.")
            return True

    except Exception as e:
        print(f"An error occurred in main(): {e}")
        return False


if __name__ == "__main__":
    if asyncio.run(main()):
        print("\nSUCCESS: Script finished.")
    else:
        print("\nFAILURE: Script ended with an error.")
