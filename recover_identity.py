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


# Full path: axon_bbs/recover_identity.py
import os
import sys
import django
import getpass
import shutil

# --- Django Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)
# --- End Django Setup ---

from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.identity_service import IdentityService
from core.services.encryption_utils import derive_key_from_password, generate_salt

User = get_user_model()

def recover_identity(username):
    """
    Deletes a user's corrupted identity files and generates a new identity,
    updating their password and public key in the process.
    """
    print(f"--- Identity Recovery for user: {username} ---")

    # 1. Find the user
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"\n[ERROR] User '{username}' not found in the database.")
        return

    # 2. Define user data paths
    user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', username)
    salt_path = os.path.join(user_data_dir, 'salt.bin')
    identity_storage_path = os.path.join(user_data_dir, 'identities.dat')

    # 3. Delete corrupted files
    print("\n[1] Deleting old identity files (if they exist)...")
    if os.path.exists(identity_storage_path):
        os.remove(identity_storage_path)
        print(f"  - Removed: {identity_storage_path}")
    if os.path.exists(salt_path):
        os.remove(salt_path)
        print(f"  - Removed: {salt_path}")

    # 4. Get a new password for the user
    print("\n[2] Please set a new password for the user.")
    try:
        new_password = getpass.getpass(f"Enter new password for '{username}': ")
        if not new_password:
            print("Password cannot be empty. Aborting.")
            return
        password_confirm = getpass.getpass("Confirm new password: ")
        if new_password != password_confirm:
            print("Passwords do not match. Aborting.")
            return
    except Exception as error:
        print(f"ERROR: Could not read password: {error}")
        return

    # 5. Generate new identity using the same logic as registration
    print("\n[3] Generating new salt and identity...")
    try:
        os.makedirs(user_data_dir, exist_ok=True)
        salt = generate_salt()
        with open(salt_path, 'wb') as f:
            f.write(salt)
        
        encryption_key = derive_key_from_password(new_password, salt)
        identity_service = IdentityService(
            storage_path=identity_storage_path,
            encryption_key=encryption_key
        )
        identity = identity_service.generate_and_add_identity(name="default")
        
        # 6. Update user model
        user.pubkey = identity['public_key']
        user.set_password(new_password)
        user.save()
        print("  - New identity generated.")
        print("  - User password and public key have been updated.")

    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred while generating the new identity: {e}")
        return

    print("\n--- ✅ RECOVERY COMPLETE ---")
    print(f"The identity for user '{username}' has been reset.")
    print("They can now log in with their new password.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python recover_identity.py <username>")
        sys.exit(1)
    
    target_username = sys.argv[1]
    recover_identity(target_username)
