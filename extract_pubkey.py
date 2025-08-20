# Full path: axon_bbs/extract_pubkey.py
import sys
from cryptography.hazmat.primitives import serialization

def extract_public_key(private_key_path):
    """
    Reads a private key PEM file and prints its corresponding public key.
    """
    try:
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None  # Assuming the key is not encrypted
            )
        
        public_key = private_key.public_key()
        
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        print("--- Public Key ---")
        print(public_key_pem.decode('utf-8'))
        
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the file path is correct and the key is not password-protected.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_pubkey.py <path_to_private_key.pem>")
        sys.exit(1)
    
    extract_public_key(sys.argv[1])
