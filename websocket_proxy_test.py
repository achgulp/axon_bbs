# axon_bbs/websocket_proxy_test.py

import asyncio
from python_socks.async_.asyncio import Proxy
import websockets

# Proxy and target details
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 9999
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
