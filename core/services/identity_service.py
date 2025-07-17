# axon_bbs/core/services/identity_service.py
import json
import os
import logging
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
# We will create this encryption utility next
from .encryption_utils import encrypt_data, decrypt_data
from pynostr.key import PrivateKey  # Use pynostr for compatible keys

logger = logging.getLogger(__name__)

class IdentityService:
    """
    Manages user Nostr key pairs with encrypted storage.
    Adapted from the IdentityManager in the 'offtherails' project.
    Each user on the BBS will have their own instance of this service,
    unlocked with their password.
    """
    def __init__(self, storage_path: str, encryption_key: bytes):
        """
        Initializes the service for a specific user.
        :param storage_path: The full path to the user's encrypted identity file.
        :param encryption_key: The key derived from the user's password to encrypt/decrypt the file.
        """
        self.storage_file = storage_path
        self.encryption_key = encryption_key
        self.identities: List[Dict[str, Any]] = []
        self._load_identities()
        logger.info(f"IdentityService instance created for storage file: {storage_path}")

    def _load_identities(self) -> None:
        """
        Loads and decrypts identities from the user's storage file.
        """
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "rb") as f:
                    encrypted_data = f.read()
                if not encrypted_data:
                    self.identities = []
                    return
                decrypted_data = decrypt_data(encrypted_data, self.encryption_key)
                self.identities = json.loads(decrypted_data)
            except Exception as e:
                logger.error(f"Failed to load identities from {self.storage_file}: {e}", exc_info=True)
                # If decryption fails (e.g., wrong password), treat as no identities
                self.identities = []
        else:
            self.identities = []
            # Don't save immediately, wait for an action.

    def _save_identities(self) -> None:
        """
        Encrypts and saves the user's current identities to their storage file.
        """
        try:
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            identities_json = json.dumps(self.identities, indent=4)
            encrypted_data = encrypt_data(identities_json, self.encryption_key)
            with open(self.storage_file, "wb") as f:
                f.write(encrypted_data)
            logger.debug(f"Saved identities to {self.storage_file}")
        except Exception as e:
            logger.error(f"Failed to save identities to {self.storage_file}: {e}", exc_info=True)

    def generate_and_add_nostr_identity(self, name: str = "default") -> Dict[str, Any]:
        """
        Generates a new Nostr key pair and adds it as an identity.
        """
        try:
            private_key = PrivateKey()
            public_key_hex = private_key.public_key.hex()
            private_key_hex = private_key.hex()
            identity = {
                "id": str(uuid.uuid4()),
                "name": name,
                "type": "nostr",
                "public_key": public_key_hex,
                "private_key": private_key_hex, # This will be encrypted on save
                "created_at": datetime.now().isoformat()
            }
            self.identities.append(identity)
            self._save_identities()
            logger.info(f"Generated Nostr identity '{name}': {public_key_hex[:8]}...")
            return identity
        except Exception as e:
            logger.error(f"Failed to generate Nostr identity: {e}", exc_info=True)
            raise

    def get_all_nostr_identities(self) -> List[Dict[str, Any]]:
        """
        Retrieves all Nostr identities for the user.
        """
        return [id_ for id_ in self.identities if id_.get("type") == "nostr"]

    def get_identity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific identity by its name.
        """
        for identity in self.identities:
            if identity.get("name") == name:
                return identity
        return None

    def remove_identity(self, identity_id: str) -> bool:
        """
        Removes an identity by its unique ID.
        """
        initial_count = len(self.identities)
        self.identities = [id_ for id_ in self.identities if id_.get("id") != identity_id]
        if len(self.identities) < initial_count:
            self._save_identities()
            logger.info(f"Removed identity: {identity_id}")
            return True
        return False
