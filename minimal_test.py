# axon_bbs/minimal_test.py

import socks
import socket

print("Configuring SOCKS proxy with remote DNS...")
try:
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9999, rdns=True)
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
