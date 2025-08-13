# Full path: axon_bbs/test_crypto_cycle.py
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

def run_crypto_test():
    print("--- Starting Self-Contained Crypto Cycle Test ---")
    try:
        # 1. Generate a dummy RSA key pair
        print("[1] Generating a new RSA key pair...")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        print("    - Success.")

        # 2. Generate a dummy AES key (this is what we're trying to protect)
        print("[2] Generating a new one-time AES key...")
        aes_key = os.urandom(32)# Full path: axon_bbs/test_crypto_cycle.py
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

def run_crypto_test():
    print("--- Starting Self-Contained Crypto Cycle Test ---")
    try:
        # 1. Generate a dummy RSA key pair
        print("[1] Generating a new RSA key pair...")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        print("    - Success.")

        # 2. Generate a dummy AES key (this is what we're trying to protect)
        print("[2] Generating a new one-time AES key...")
        aes_key = os.urandom(32)
        print(f"    - AES Key (first 8 bytes): {aes_key[:8].hex()}...")

        # 3. Encrypt the AES key with the RSA public key (create the "envelope")
        print("[3] Encrypting the AES key with the public key...")
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print("    - Success.")

        # 4. Decrypt the AES key with the RSA private key (open the "envelope")
        print("[4] Decrypting the AES key with the private key...")
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
            print( "    - Success, keys match.")
        else:
            print( "    - FAILURE, keys DO NOT match.")
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
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

        if decrypted_data == b"test message":
             print( "    - Success, AES cycle complete.")
        else:
            print( "    - FAILURE, AES data does not match.")
            return

        print("\n--- ✅ CRYPTO CYCLE SUCCEEDED ---")

    except Exception as e:
        print(f"\n--- ❌ CRYPTO CYCLE FAILED ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_crypto_test()
        print(f"    - AES Key (first 8 bytes): {aes_key[:8].hex()}...")

        # 3. Encrypt the AES key with the RSA public key (create the "envelope")
        print("[3] Encrypting the AES key with the public key...")
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print("    - Success.")

        # 4. Decrypt the AES key with the RSA private key (open the "envelope")
        print("[4] Decrypting the AES key with the private key...")
        decrypted_aes_key = private_key.decrypt(
            encrypted_aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print(f"    - Decrypted AES Key (first 8 bytes): {decrypted_aes_key[:8].hex()}...")

        # 5. Verify that the decrypted key matches the original# Full path: axon_bbs/test_crypto_cycle.py
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

def run_crypto_test():
    print("--- Starting Self-Contained Crypto Cycle Test ---")
    try:
        # 1. Generate a dummy RSA key pair
        print("[1] Generating a new RSA key pair...")
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        print("    - Success.")

        # 2. Generate a dummy AES key (this is what we're trying to protect)
        print("[2] Generating a new one-time AES key...")
        aes_key = os.urandom(32)
        print(f"    - AES Key (first 8 bytes): {aes_key[:8].hex()}...")

        # 3. Encrypt the AES key with the RSA public key (create the "envelope")
        print("[3] Encrypting the AES key with the public key...")
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print("    - Success.")

        # 4. Decrypt the AES key with the RSA private key (open the "envelope")
        print("[4] Decrypting the AES key with the private key...")
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
            print( "    - Success, keys match.")
        else:
            print( "    - FAILURE, keys DO NOT match.")
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
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

        if decrypted_data == b"test message":
             print( "    - Success, AES cycle complete.")
        else:
            print( "    - FAILURE, AES data does not match.")
            return

        print("\n--- ✅ CRYPTO CYCLE SUCCEEDED ---")

    except Exception as e:
        print(f"\n--- ❌ CRYPTO CYCLE FAILED ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_crypto_test()
        print("[5] Verifying keys match...")
        if decrypted_aes_key == aes_key:
            print( "    - Success, keys match.")
        else:
            print( "    - FAILURE, keys DO NOT match.")
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
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

        if decrypted_data == b"test message":
             print( "    - Success, AES cycle complete.")
        else:
            print( "    - FAILURE, AES data does not match.")
            return

        print("\n--- ✅ CRYPTO CYCLE SUCCEEDED ---")

    except Exception as e:
        print(f"\n--- ❌ CRYPTO CYCLE FAILED ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_crypto_test()
