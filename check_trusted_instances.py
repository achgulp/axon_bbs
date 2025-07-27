# Full path: axon_bbs/check_trusted_instances.py
# Standalone script: save as check_trusted_instances.py and run with python check_trusted_instances.py
# Must be run from the project root (where manage.py is) with virtualenv activated.
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
django.setup()

from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum

# Fetch local instance (the one with an encrypted private key)
local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()

if local_instance:
    print("--- LOCAL INSTANCE ---")
    local_pubkey = local_instance.pubkey
    if local_pubkey:
        print(f"Local pubkey checksum: {generate_checksum(local_pubkey)}")
        print(f"Pubkey (full): {local_pubkey}")
    else:
        print("Local instance has no pubkey.")
else:
    print("No local instance found.")

print("\n--- TRUSTED PEERS ---")
# Fetch trusted peers (must have is_trusted_peer=True)
peers = TrustedInstance.objects.filter(is_trusted_peer=True)
num_peers = peers.count()
print(f"Number of trusted peers loaded: {num_peers}")

if num_peers > 0:
    print("Trusted peers are loaded. Their checksums are:")
    expected_checksums = []
    for peer in peers:
        pubkey = peer.pubkey
        if pubkey:
            checksum = generate_checksum(pubkey)
            expected_checksums.append(checksum)
            print(f"\n- Peer ID {peer.id} ({peer.web_ui_onion_url or 'No URL'})")
            print(f"  Checksum: {checksum}")
            print(f"  Pubkey (full): {pubkey}")
        else:
            print(f"- Peer ID {peer.id} has no pubkey.")
    print(f"\nExpected checksums list: {', '.join(expected_checksums)}")
else:
    print("No trusted peers loaded (Expected checksums: None).")
    print("NOTE: Please go to the admin panel, select the peer instance(s), and ensure the 'is_trusted_peer' box is checked.")
