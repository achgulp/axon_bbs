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

    print("\n[1] Checking for Local Instance(s)...")
    # UPDATED: Check for all instances with a private key, not just the first one.
    local_instances = TrustedInstance.objects.filter(encrypted_private_key__isnull=False)
    count = local_instances.count()

    if count == 1:
        local_instance = local_instances.first()
        print("  Status: OK - Found exactly one local instance.")
        local_pubkey = local_instance.pubkey
        if local_pubkey:
            print(f"  URL: {local_instance.web_ui_onion_url or 'Not Set'}")
            print(f"  --- This is your VM's correct identity ---")
            print(f"  Local Pubkey Checksum: {generate_checksum(local_pubkey)}")
            print(f"  ---")
        else:
            print("  Warning: Local instance found but has no public key.")
    elif count > 1:
        print(f"  Status: FATAL ERROR - Found {count} instances with encrypted private keys.")
        print("  There should be exactly one. This 'split brain' identity is the cause of your decryption errors.")
        print("  The service is likely loading the wrong private key when trying to decrypt messages.")
        print("\n  >>> ACTION: Go to the admin panel on this VM, find the incorrect local instance(s) below, and DELETE them, leaving only the correct one for this VM. <<<")
        for instance in local_instances:
            print(f"  - Found conflicting instance for URL: {instance.web_ui_onion_url or 'URL Not Set'}")
    else: # count == 0
        print("  Status: NOT FOUND - No local instance with an encrypted private key was found.")
        print("  ACTION: Go to the admin panel, create an instance for this VM, and use the 'Generate and encrypt keys' action.")


if __name__ == "__main__":
    check_instances()
