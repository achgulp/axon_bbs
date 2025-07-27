# Full path: axon_bbs/test_sync_endpoint.py
# A standalone script to test the GET /api/sync/ endpoint.
# Run from your laptop to the host machine.
import requests
import base64
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone

# --- CONFIGURATION ---
# The .onion address of the HOST machine you are testing against.
TARGET_ONION_URL = "http://lpa4klsh6xbzlexh6pwdxtn7ezr4snztgyxxgejtbmvpl4zw6sqljoyd.onion"

# The private and public keys of the LAPTOP (the machine running this script).
# These must correspond to the public key you added as a TrustedInstance on the HOST.
PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCX0Zvp5GicutPw
lj6nOVxXJ6mZ2IBOVZduLsh//hpFgsHSPeVbjQ2toawm3eXaplKxDX2hqX22C4/L
wVtTvYcCdztK1HgMDVopILBGm66qZ0E8mPzhnBZ8INAuEkq32023xljyPU4RkyMg
Y9sUAs9FLqfYrjHCRAGeXXdV/n1YtQoCb1fP/bkm26lF2sDpxMoX6/sCduK0haGs
Hl9FTfpL8yccBfFcciZb9YfPOwceL66Nvy9/FOXXGuRMfoCjUwRzBlc4WVB7FubA
rKkskg4Ool5OSgRqbofmsAFd62w0VLTOmZxVmEtrRVbhhxl45156IyFFKxDWG8Dp
FBL/Gu5vAgMBAAECggEAEgQErXe2VkrxVY5utudeptUFEkWXzDPp+WBB2LZtpawD
lhBURE3zvpP92srgONcd3vbL3sA/M7ghgztZvBE0kT1W4uVdrYh0F4dSg757tqr0
Gd3JvHgKTwaRzbXL+g9jJJi7+1r9BabhNznCSJigwgPsVREuxG/PhVxwCdteQoVi
YqmhopSHEqDHnNmwrZB5QNo1akiTuAZO354Yn+0nHbRwPSqGicNLye5bHzb1NkYr
jyl3IstT5sy3bKDpF44xRN3Vy0PYIYbwcqAtUsZnM0l2eoPZdB9tYWB7/CCMhfFC
QsH81q8+pxI9aCD1DVE9zitZBCFovDsi2Jy4BpNo6QKBgQDQkdRHK0fXYY3COpTv
1/9SimsDVU1FPTmOSmIOITKZdsHZHdjd+fVs4lS5I/nf152iCLSu5nEEc1Yws1Im
ChIE01kFKdpuzEYWw9JJb8v+LrwQRgYgfGpBlNaMSVYmrbWRq1GHvzEK7La+JL9o
7T7mzmggZGXYm/rd4z5LjRqDlQKBgQC6V/Ms8g+5tHSSn2RQWnLIt33McH7niy2y
NidbYK6/tLe1f658BSvcXDpdtcCpfW54cgv5S+Tep0MQlEHskqDLYbCXLiQuPKe7
bbTyyCOlwi+nJBHbTmc9xIF9WwJWypqFqNpYtGvh2I6lkCosTnzQkVNXAe/zeV4L
jXhFrK3o8wKBgQClVSRQMkflvSgxclzD75Yu6RjBcKorG8h3OhGWn8xLiK9Lm/Rg
qhdZ8+QzSwh136bOXlZUWsn2PDNzsYKKMutrtdnYVQAZWoao3xvgKOYtHQDpaYjL
0bQtPn4AgNXxHTxUN9kOYYnP3itSeTDeTUrSjYZPPybY2XS41b15CGafLQKBgQCi
y4loP8VbQPsCyXuS86IKFrwxaiqEUMRISCVUIIAqfVBtoTGnqcDq0CwxiELcD/f+
A+zQC+zUVB40EsIRUvxlEmB7g1Uai+UhyrNl01HJU3/cLpfnF3T8sntKL8M4XeJn
WOAA1QbXFSFyJSOi96L1d7Dud4PRGrv9rcdgX37D3wKBgEonGpYFqzB5ehdLSWh8
9aEeoggDGqtYZ8PXRAOeIbCyxSkiRQIazi0BElt7UdQnDGzIfmMmcez5W1uIWnRy
Z5t7PEorJedH5LSSxy6LdmRicGEaMYAMQqXcxlGUPSYdyC85BAvDhhxoYIMblfIM
19BXxGirzP2ryKSSQe7sO4q8
-----END PRIVATE KEY-----"""
SENDER_PUBKEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAl9Gb6eRonLrT8JY+pzlc
VyepmdiATlWXbi7If/4aRYLB0j3lW40NraGsJt3l2qZSsQ19oal9tguPy8FbU72H
Anc7StR4DA1aKSCwRpuuqmdBPJj84ZwWfCDQLhJKt9tNt8ZY8j1OEZMjIGPbFALP
RS6n2K4xwkQBnl13Vf59WLUKAm9Xz/25JtupRdrA6cTKF+v7AnbitIWhrB5fRU36
S/MnHAXxXHImW/WHzzsHHi+ujb8vfxTl1xrkTH6Ao1MEcwZXOFlQexbmwKypLJIO
DqJeTkoEam6H5rABXetsNFS0zpmcVZhLa0VW4YcZeOdeeiMhRSsQ1hvA6RQS/xru
bwIDAQAB
-----END PUBLIC KEY-----"""
# -----------------------------------------------------------------------

# The Tor SOCKS proxy running on your machine
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

# --- SCRIPT LOGIC ---
def run_test():
    """Signs and sends the GET request to the /api/sync/ endpoint."""
    print(f"[*] Preparing request to: {TARGET_ONION_URL}")

    # 1. Load private key for signing
    try:
        private_key = serialization.load_pem_private_key(PRIVATE_KEY_PEM.encode(), password=None)
    except Exception as e:
        print(f"\n[FAILURE] Could not load private key. Error: {e}")
        return

    # 2. Prepare data for signing (the timestamp)
    #    FIX: Generate a timezone-aware timestamp using timezone.utc
    timestamp = datetime.now(timezone.utc).isoformat()
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(timestamp.encode())
    digest = hasher.finalize()

    # 3. Sign the digest
    signature = private_key.sign(
        digest,
        PSS(mgf=MGF1(hashes.SHA256()), salt_length=PSS.MAX_LENGTH),
        hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode('utf-8')

    # 4. Assemble headers for authentication
    # The public key is also Base64 encoded to prevent issues with newlines in headers
    headers = {
        'X-Timestamp': timestamp,
        'X-Signature': signature_b64,
        'X-Pubkey': base64.b64encode(SENDER_PUBKEY_PEM.encode()).decode('utf-8')
    }

    # 5. Construct the final URL with the 'since' parameter
    since_param = "0001-01-01T00:00:00+00:00"
    target_url = f"{TARGET_ONION_URL.rstrip('/')}/api/sync/?since={since_param}"

    print(f"[*] Target URL: {target_url}")
    print(f"[*] Using Tor SOCKS proxy at: {proxies['http']}")
    print("\n--- Request Headers ---")
    print(json.dumps(headers, indent=2))
    print("-----------------------\n")

    # 6. Send the request over Tor
    try:
        print("[*] Sending GET request...")
        response = requests.get(
            target_url,
            headers=headers,
            proxies=proxies,
            timeout=120  # Increased timeout for Tor
        )

        print("\n--- Response ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body:\n{response.text}")
        print("----------------\n")

        if response.status_code == 200:
            print("[SUCCESS] The request was successful!")
        else:
            print(f"[FAILURE] The request failed with status code {response.status_code}.")
            if response.status_code == 401:
                print("Reason: 401 Unauthorized. This means the host server does not trust your public key.")
                print("ACTION: Ensure the laptop's SENDER_PUBKEY_PEM is in the host's TrustedInstance table AND the 'is_trusted_peer' checkbox is checked.")

    except requests.exceptions.RequestException as e:
        print("\n[FAILURE] The connection failed.")
        print(f"Error: {e}")

if __name__ == '__main__':
    run_test()
