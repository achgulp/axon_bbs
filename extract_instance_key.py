# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/extract_instance_key.py
# Standalone script to decrypt and display the local instance's private key.
import os
import sys
import django
from cryptography.fernet import Fernet
import base64

# --- Django Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
django.setup()
# --- End Django Setup ---

from django.conf import settings
from core.models import TrustedInstance

def extract_instance_key():
    """
    Finds the local instance, decrypts its private key using the
    Django SECRET_KEY, and prints it to the console.
    """
    print("[*] Searching for local trusted instance in the database...")

    # 1. Find the local instance (it's the only one with an encrypted key)
    local_instance = TrustedInstance.objects.filter(
        encrypted_private_key__isnull=False
    ).first()

    if not local_instance:
        print("\n[ERROR] No local instance with an encrypted private key was found.")
        print("Please ensure you have generated keys for your instance via the admin panel.")
        return

    print(f"[*] Found local instance for URL: {local_instance.web_ui_onion_url}")

    # 2. Derive the decryption key from the Django SECRET_KEY
    try:
        if not settings.SECRET_KEY:
            raise ValueError("SECRET_KEY is not set in your settings or .env file.")
        
        # This logic matches the encryption method in core/admin.py
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
    except Exception as e:
        print(f"\n[ERROR] Could not prepare the decryption key: {e}")
        return

    # 3. Decrypt and print the private key
    try:
        encrypted_key = local_instance.encrypted_private_key
        decrypted_pem = f.decrypt(encrypted_key.encode()).decode('utf-8')

        print("\n--- SUCCESS ---")
        print("Unencrypted Instance Private Key:")
        print(decrypted_pem)
        print("--- END KEY ---")

    except Exception as e:
        print(f"\n[ERROR] Failed to decrypt the private key. Is your SECRET_KEY correct?")
        print(f"Details: {e}")

if __name__ == "__main__":
    extract_instance_key()
