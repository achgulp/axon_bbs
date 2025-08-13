# Full path: axon_bbs/check_trusted_instances.py
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from core.models import TrustedInstance
from core.services.encryption_utils import generate_checksum

def check_instances():
    print("--- Axon BBS Instance Diagnostic Tool ---")

    print("\n[1] Checking for Local Instance...")
    local_instance = TrustedInstance.objects.filter(encrypted_private_key__isnull=False).first()

    if local_instance:
        print("  Status: OK - Local instance found.")
        local_pubkey = local_instance.pubkey
        if local_pubkey:
            print(f"  URL: {local_instance.web_ui_onion_url or 'Not Set'}")
            print(f"  --- COPY THE ENTIRE BLOCK BELOW ---")
            print(f"  Local Pubkey:\n{local_pubkey}")
            print(f"  Local Pubkey Checksum: {generate_checksum(local_pubkey)}")
            print(f"  --- END COPY BLOCK ---")
        else:
            print("  Warning: Local instance found but has no public key.")
    else:
        print("  Status: NOT FOUND - No local instance configured.")

if __name__ == "__main__":
    check_instances()
