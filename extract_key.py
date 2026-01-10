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


# Full path: axon_bbs/extract_key.py
# Standalone script to decrypt and display a user's private key.
import os
import sys
import django
import getpass

# --- Django Setup ---
# This allows the script to use the project's models and services.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
django.setup()
# --- End Django Setup ---

from django.conf import settings
from accounts.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password

def extract_private_key():
    """
    Prompts for user credentials, decrypts the identity file,
    and prints the unencrypted private key.
    """
    # 1. Get user credentials
    username = input("Enter the username for the key you want to extract: ")
    if not username:
        print("Username cannot be empty.")
        return

    try:
        password = getpass.getpass(f"Enter password for user '{username}': ")
    except Exception as error:
        print(f"ERROR: Could not read password: {error}")
        return

    # 2. Construct paths to the user's data files
    user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', username)
    salt_path = os.path.join(user_data_dir, 'salt.bin')
    identity_storage_path = os.path.join(user_data_dir, 'identities.dat')

    if not os.path.exists(salt_path) or not os.path.exists(identity_storage_path):
        print(f"ERROR: Data files for user '{username}' not found.")
        print("Please ensure the username is correct and the server has been run at least once for this user.")
        return

    # 3. Derive the encryption key from the password and salt
    try:
        with open(salt_path, 'rb') as f:
            salt = f.read()
        encryption_key = derive_key_from_password(password, salt)
    except Exception as e:
        print(f"ERROR: Could not derive encryption key. Details: {e}")
        return

    # 4. Use the IdentityService to load and decrypt the keys
    try:
        identity_service = IdentityService(
            storage_path=identity_storage_path,
            encryption_key=encryption_key
        )
        # The IdentityService automatically loads and decrypts upon initialization
        identity = identity_service.get_identity_by_name("default")

        if not identity:
            print("\n---")
            print("ERROR: Could not decrypt or find the 'default' identity.")
            print("This usually means the password was incorrect.")
            print("---")
            return

        private_key = identity.get('private_key')

        if not private_key:
            print("ERROR: Identity found, but it does not contain a private key.")
            return

        # 5. Print the unencrypted private key
        print("\n--- SUCCESS ---")
        print("Unencrypted Private Key for user '{}':".format(username))
        print(private_key)
        print("--- END KEY ---")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    extract_private_key()
