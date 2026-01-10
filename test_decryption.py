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


# Full path: axon_bbs/test_decryption.py
import os
import sys
import django
import traceback
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
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
from django.db.models import Q
from core.models import TrustedInstance, Message, FileAttachment

# --- End Django Setup ---

def run_decryption_test():
    print("--- Stored Content Decryption Test ---")
    
    try:
        # 1. Find all available content and display a list
        print("\n[1] Searching for available content in the database...")
        messages = Message.objects.filter(manifest__isnull=False)
        files = FileAttachment.objects.filter(manifest__isnull=False)
        all_content = list(messages) + list(files)

        if not all_content:
            print("   - No content with manifests found in the database.")
            return

        print(f"   - Found {len(all_content)} item(s) available for testing:")
        for i, item in enumerate(all_content):
            content_type = "Message" if isinstance(item, Message) else "File"
            name = item.subject if isinstance(item, Message) else item.filename
            hash_short = item.manifest.get('content_hash', 'N/A')[:12]
            print(f"  [{i+1}] {content_type}: '{name}' (hash: {hash_short}...)")

        # 2. Get user input
        choice = input("\nEnter the number of the content to test: ")
        selected_index = int(choice) - 1

        if not (0 <= selected_index < len(all_content)):
            print("Invalid selection.")
            return

        selected_item = all_content[selected_index]
        content_hash = selected_item.manifest.get('content_hash')
        manifest = selected_item.manifest
        
        print(f"\n[2] Testing content with hash: {content_hash[:12]}...")

        # 3. Assemble the encrypted data from chunks on disk
        print("[3] Assembling encrypted data from local chunks...")
        chunk_storage_path = os.path.join(settings.BASE_DIR, 'data', 'bitsync_chunks')
        content_chunk_dir = os.path.join(chunk_storage_path, content_hash)
        
        num_chunks = len(manifest.get('chunk_hashes', []))
        encrypted_data = b""
        for i in range(num_chunks):
            chunk_path = os.path.join(content_chunk_dir, f"{i}.chunk")
            if not os.path.exists(chunk_path):
                print(f"   - FAILURE: Chunk {i} is missing from disk at {chunk_path}")
                return
            with open(chunk_path, 'rb') as f:
                encrypted_data += f.read()
        
        print(f"   - Success: Assembled {len(encrypted_data)} bytes from {num_chunks} chunk(s).")

        # 4. Load the local private key
        print("[4] Loading and decrypting local instance private key...")
        local_instance = TrustedInstance.objects.get(encrypted_private_key__isnull=False, is_trusted_peer=False)
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
        f = Fernet(key)
        decrypted_pem = f.decrypt(local_instance.encrypted_private_key.encode())
        private_key = serialization.load_pem_private_key(decrypted_pem, password=None)
        print("   - Success: Key loaded.")

        # 5. Attempt to decrypt the AES key from the manifest's envelope
        print("[5] Attempting to open the encryption envelope...")
        try:
            from core.services.encryption_utils import generate_checksum
            local_checksum = generate_checksum(local_instance.pubkey)
        except ImportError:
            local_checksum = base64.b64encode(hashlib.md5(local_instance.pubkey.strip().encode()).digest()).decode()


        encrypted_aes_key_b64 = manifest['encrypted_aes_keys'].get(local_checksum)
        if not encrypted_aes_key_b64:
            print(f"   - FAILURE: Could not find an encryption envelope for our key (checksum: {local_checksum}) in the manifest.")
            print(f"   - Available checksums in manifest are: {list(manifest['encrypted_aes_keys'].keys())}")
            return
        
        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        print(f"   - Success: Envelope opened. AES Key: {aes_key.hex()[:16]}...")
        
        # 6. Attempt to decrypt the content
        print("[6] Attempting to decrypt content with AES key...")
        iv = base64.b64decode(manifest['encryption_iv'])
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_data = unpadder.update(padded_data) + unpadder.finalize()
        print("   - Success: Decryption and unpadding complete.")

        print("\n--- ✅ DECRYPTION SUCCEEDED ---")
        try:
            content = json.loads(decrypted_data)
            print("Decrypted Content (JSON):")
            print(json.dumps(content, indent=2))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"Decrypted Content (Raw Bytes, first 256):")
            print(decrypted_data[:256])

    except Exception as e:
        print(f"\n--- ❌ DECRYPTION FAILED ---")
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_decryption_test()
