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

# Fetch local instance (with encrypted_private_key)
local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()

if local_instance:
    print("Local instance found.")
    local_pubkey = local_instance.pubkey
    if local_pubkey:
        print(f"Local pubkey (length: {len(local_pubkey)}): {local_pubkey[:100]}...{local_pubkey[-100:]}")
        print(f"Local checksum: {generate_checksum(local_pubkey)}")
    else:
        print("Local instance has no pubkey.")
else:
    print("No local instance found.")

# Fetch trusted peers (excluding local)
peers = TrustedInstance.objects.exclude(encrypted_private_key__isnull=False)
num_peers = peers.count()
print(f"Number of trusted peers loaded (excluding local): {num_peers}")

if num_peers > 0:
    print("Trusted peers are loaded.")
    expected_checksums = []
    for peer in peers:
        pubkey = peer.pubkey
        if pubkey:
            checksum = generate_checksum(pubkey)
            expected_checksums.append(checksum)
            print(f"Peer ID {peer.id} pubkey (length: {len(pubkey)}): {pubkey[:100]}...{pubkey[-100:]}")
            print(f"Peer ID {peer.id} checksum: {checksum}")
        else:
            print(f"Peer ID {peer.id} has no pubkey.")
    print(f"Expected checksums: {', '.join(expected_checksums) or 'None'}")
else:
    print("No trusted peers loaded (expected checksums: None).")
