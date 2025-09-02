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


# Full path: axon_bbs/test_crypto_cycle.py
import os
import sys
import django
import traceback
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

# --- Django Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from django.conf import settings
from core.models import TrustedInstance
# --- End Django Setup ---


def run_crypto_test():
    print("--- Starting Crypto Cycle Test with Stored Instance Key ---")
    private_key = None
    try:
        # 1. Load and decrypt the local instance's private key from the database
        print("[1] Loading and decrypting local instance private key...")
        local_instance = TrustedInstance.objects.get(
            encrypted_private_key__isnull=False, 
            is_trusted_peer=False
        )
        
        if not (local_instance and local_instance.encrypted_private_key):
            raise ValueError("Local instance with an encrypted private key was not found.")

        # Derive the decryption key from the Django SECRET_KEY
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        decrypted_pem = f.decrypt(local_instance.encrypted_private_key.encode())
        
        # Load the private key object
        private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
        public_key = private_key.public_key()
        print("    - Success. Key loaded.")

        # 2. Generate a dummy AES key (this is what we're trying to protect)
        print("[2] Generating a new one-time AES key...")
        aes_key = os.urandom(32)
        print(f"    - AES Key (first 8 bytes): {aes_key[:8].hex()}...")

        # 3. Encrypt the AES key with the public key (create the "envelope")
        print("[3] Encrypting the AES key with the instance's public key...")
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print("    - Success.")

        # 4. Decrypt the AES key with the private key (open the "envelope")
        print("[4] Decrypting the AES key with the instance's private key...")
        decrypted_aes_key = private_key.decrypt(
            encrypted_aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print(f"    - Decrypted AES Key (first 8 bytes): {decrypted_aes_key[:8].hex()}...")

        # 5. Verify that the decrypted key matches the original
        print("[5] Verifying keys match...")
        if decrypted_aes_key == aes_key:
            print("    - Success, keys match.")
        else:
            print("    - FAILURE, keys DO NOT match.")
            return

        # 6. Test a full AES cycle just to be sure
        print("[6] Performing a test AES encryption/decryption cycle...")
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(decrypted_aes_key), modes.CBC(iv))
        
        # Encrypt
        padder = PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(b"test message") + padder.finalize()
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Decrypt
        decryptor = cipher.decryptor()
        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

        if decrypted_data == b"test message":
            print("    - Success, AES cycle complete.")
        else:
            print("    - FAILURE, AES data does not match.")
            return

        print("\n--- ✅ CRYPTO CYCLE SUCCEEDED ---")

    except Exception as e:
        print(f"\n--- ❌ CRYPTO CYCLE FAILED ---")
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_crypto_test()
