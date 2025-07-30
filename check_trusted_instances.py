# Full path: axon_bbs/check_trusted_instances.py
# Standalone script: save as check_trusted_instances.py and run with `python check_trusted_instances.py`
# Must be run from the project root (where manage.py is) with the virtualenv activated.
import os
import sys
import django

# --- Django Setup ---
# This allows the script to use the project's models and services.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print("Please ensure you are running this script from the 'axon_bbs' project root directory.")
    sys.exit(1)
# --- End Django Setup ---

from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum

def check_instances():
    """
    Queries the database for the local instance and trusted peers,
    then prints their details and checksums for verification.
    """
    print("--- Axon BBS Instance Diagnostic Tool ---")

    # 1. Fetch local instance (the one with an encrypted private key)
    print("\n[1] Checking for Local Instance...")
    local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()

    if local_instance:
        print("  Status: OK - Local instance found.")
        local_pubkey = local_instance.pubkey
        if local_pubkey:
            print(f"  URL: {local_instance.web_ui_onion_url or 'Not Set'}")
            print(f"  Local Pubkey Checksum: {generate_checksum(local_pubkey)}")
        else:
            print("  Warning: Local instance found but has no public key.")
    else:
        print("  Status: NOT FOUND - No local instance configured in the database.")
        print("  ACTION: Go to the admin panel, create an instance for your BBS, and use the 'Generate and encrypt keys' action.")

    # 2. Fetch trusted peers (must have is_trusted_peer=True)
    print("\n[2] Checking for Trusted Peers...")
    # This query mimics the one in the permission class.
    peers = TrustedInstance.objects.filter(is_trusted_peer=True)
    num_peers = peers.count()
    
    print(f"  Status: Found {num_peers} instance(s) marked as 'is_trusted_peer'.")

    if num_peers > 0:
        print("  Details of trusted peers:")
        expected_checksums = []
        for i, peer in enumerate(peers):
            pubkey = peer.pubkey
            if pubkey:
                checksum = generate_checksum(pubkey)
                expected_checksums.append(checksum)
                print(f"\n  - Peer #{i+1}:")
                print(f"    URL: {peer.web_ui_onion_url or 'URL not set'}")
                print(f"    Checksum: {checksum}")
            else:
                print(f"\n  - Peer #{i+1} (ID: {peer.id}) has no pubkey and will be ignored.")
        
        print("\n[3] Conclusion")
        print("  The API will expect requests from peers with the following checksums:")
        print(f"  Expected Checksums List: {', '.join(expected_checksums)}")
        print("  If a peer is missing, ensure its 'is_trusted_peer' box is checked in the admin panel.")
    else:
        print("\n[3] Conclusion")
        print("  The API is not configured to trust ANY peers.")
        print("  This is why you are seeing 'Expected: None' in the logs and getting 401 Unauthorized errors.")
        print("\n  >>> ACTION: Go to the admin panel, select the peer instance(s) you want to sync with, and ensure the 'is_trusted_peer' box is checked and saved. <<<")

if __name__ == "__main__":
    check_instances()
