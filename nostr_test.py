# axon_bbs/nostr_test.py

import socks
import socket
# Force all Python networking to go through the SOCKS proxy
# rdns=True tells PySocks to let the proxy handle the DNS lookup
socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9999, rdns=True)
socket.socket = socks.socksocket

# The rest of your script remains the same
import ssl
import time
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager
from pynostr.event import Event

# 1. Generate a new private key for the test
private_key = PrivateKey()
public_key = private_key.public_key
print(f"Using new private key: {private_key.bech32()}")
print(f"Corresponding public key: {public_key.bech32()}")

# 2. Connect to Nostr relays
relay_manager = RelayManager()
relay_manager.add_relay("wss://relay.damus.io")
relay_manager.add_relay("wss://nostr-pub.wellorder.net")

print("\nAttempting to open connections...")
# NOTE: Using CERT_NONE is insecure and for testing only
relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE})
time.sleep(2) # Allow time for connections to open

print("Connections established, creating event...")

# 3. Create and sign the event (a simple text note)
event = Event(content="Hello Nostr from a Python script!")
event.sign(private_key.hex())

# 4. Publish the event to the relays
print("Publishing event...")
relay_manager.publish_event(event)
print("Event published!")

# 5. Close connections
time.sleep(1) # Allow time for publishing
relay_manager.close_connections()
print("Connections closed.")
