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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/core/services/identity_service.py
import json
import os
import logging
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
from .encryption_utils import derive_key_from_password, generate_salt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)

class DecryptionError(Exception):
    """Raised when a file cannot be decrypted, likely due to a wrong password/key."""
    pass

class IdentityService:
    def __init__(self, user):
        self.user = user
        self.user_data_dir = os.path.join(settings.BASE_DIR, 'data', 'user_data', self.user.username)
        self.identity_storage_path = os.path.join(self.user_data_dir, 'identities.dat')
        self.manifest_path = os.path.join(self.user_data_dir, 'identity_key_manifest.json')
        os.makedirs(self.user_data_dir, exist_ok=True)

    def _encrypt_identities(self, identities_json: str, master_aes_key: bytes) -> bytes:
        f = Fernet(master_aes_key)
        return f.encrypt(identities_json.encode())

    def _decrypt_identities(self, encrypted_data: bytes, master_aes_key: bytes) -> str:
        f = Fernet(master_aes_key)
        return f.decrypt(encrypted_data).decode()

    def get_master_key_from_password(self, password: str) -> Optional[bytes]:
        """Attempt to get the master AES key using the main password."""
        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            salt = bytes.fromhex(manifest['password_salt'])
            derived_key = derive_key_from_password(password, salt)
            
            f = Fernet(derived_key)
            master_aes_key = f.decrypt(bytes.fromhex(manifest['envelopes']['password']))
            return master_aes_key
        except (FileNotFoundError, KeyError, InvalidToken) as e:
            logger.warning(f"Failed to get master key with password for {self.user.username}: {e}")
            raise DecryptionError("Invalid password.")
        except Exception as e:
            logger.error(f"An unexpected error occurred getting master key for {self.user.username}: {e}")
            return None

    def generate_identity_with_manifest(self, password, sq1, sa1, sq2, sa2):
        """Generates a new identity and a recovery manifest for a new user."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key_pem = private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
        private_key_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()).decode('utf-8')
        
        identity = {
            "id": str(uuid.uuid4()), "name": "default", "type": "rsa",
            "public_key": public_key_pem, "private_key": private_key_pem,
            "created_at": datetime.now().isoformat()
        }
        identities_json = json.dumps([identity])

        master_aes_key = Fernet.generate_key()

        password_salt = generate_salt()
        password_derived_key = derive_key_from_password(password, password_salt)
        password_envelope = Fernet(password_derived_key).encrypt(master_aes_key)

        sq1_derived_key = derive_key_from_password(sa1, sq1.encode('utf-8'))
        sq1_envelope = Fernet(sq1_derived_key).encrypt(master_aes_key)

        sq2_derived_key = derive_key_from_password(sa2, sq2.encode('utf-8'))
        sq2_envelope = Fernet(sq2_derived_key).encrypt(master_aes_key)

        manifest = {
            "password_salt": password_salt.hex(),
            "security_question_1": sq1,
            "security_question_2": sq2,
            "envelopes": {
                "password": password_envelope.hex(),
                "sq1": sq1_envelope.hex(),
                "sq2": sq2_envelope.hex()
            }
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        encrypted_identities = self._encrypt_identities(identities_json, master_aes_key)
        with open(self.identity_storage_path, 'wb') as f:
            f.write(encrypted_identities)
            
        return identity

    def get_unlocked_private_key(self, password: str) -> Optional[str]:
        """Gets the decrypted private key using the main password."""
        master_key = self.get_master_key_from_password(password)
        if not master_key:
            return None
        
        try:
            with open(self.identity_storage_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_json = self._decrypt_identities(encrypted_data, master_key)
            identities = json.loads(decrypted_json)
            return identities[0].get('private_key')
        except Exception as e:
            logger.error(f"Failed to get unlocked private key for {self.user.username}: {e}")
            return None

    # --- NEW METHODS for password recovery ---
    def get_security_questions(self) -> Optional[Dict[str, str]]:
        """Reads the manifest and returns the user's security questions."""
        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            return {
                "security_question_1": manifest.get("security_question_1"),
                "security_question_2": manifest.get("security_question_2"),
            }
        except (FileNotFoundError, KeyError):
            return None

    def recover_identity_with_answers(self, sa1, sa2, new_password):
        """Attempts to recover the master key and resets the password envelope."""
        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
            
            sq1 = manifest['security_question_1']
            sq2 = manifest['security_question_2']

            # Attempt to decrypt with answer 1
            sq1_derived_key = derive_key_from_password(sa1, sq1.encode('utf-8'))
            master_key_1 = Fernet(sq1_derived_key).decrypt(bytes.fromhex(manifest['envelopes']['sq1']))

            # Attempt to decrypt with answer 2
            sq2_derived_key = derive_key_from_password(sa2, sq2.encode('utf-8'))
            master_key_2 = Fernet(sq2_derived_key).decrypt(bytes.fromhex(manifest['envelopes']['sq2']))

            if master_key_1 != master_key_2:
                raise DecryptionError("Recovery key mismatch.")

            master_aes_key = master_key_1
            
            # Success! Now, create a new password envelope
            new_password_salt = generate_salt()
            new_password_derived_key = derive_key_from_password(new_password, new_password_salt)
            new_password_envelope = Fernet(new_password_derived_key).encrypt(master_aes_key)

            # Update the manifest with the new password salt and envelope
            manifest['password_salt'] = new_password_salt.hex()
            manifest['envelopes']['password'] = new_password_envelope.hex()

            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            return True
        except (InvalidToken, DecryptionError):
            logger.warning(f"Failed recovery attempt for {self.user.username}: one or more answers were incorrect.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during recovery for {self.user.username}: {e}")
            return False
