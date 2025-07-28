# Full path: axon_bbs/test_sync_endpoint.py
# A standalone script to test the GET /api/sync/ endpoint.
# Run from your HOST to the LAPTOP machine.
import requests
import base64
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import PSS, MGF1
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone

# --- CONFIGURATION ---
# The .onion address of the LAPTOP machine you are testing against.
TARGET_ONION_URL = "http://irvgoajs5slszfroepj5fpit3lcxn5gxpeffim3shjstb6akbjuuzdid.onion"

# The private and public keys of the HOST (the machine running this script).
PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7vI0Epq6ixLBV
R28HWOljbFnLS+haDWIiZ7+3eG32d+eYd8W1tOIWn174qce7ap5sEM+rYn9ac8/L
rxV9Osn0qHggekHFqu6eyvgBDC3mRksuAeYsWg4dL183qg74ySnTpNs32PDwxRHc
DumrfAPgvjOdvOOp4ljC+rjnXcjO7x8JqTPghKV/G8pKqyM+xri3NDATGGnJmrNx
En6EoezpkT22jWiQR8e0omz/EQYhGapfPWrOQIuQddKVxOy5MdERj9mgnpo2S7Oy
Tgvw/wzOP1GqSmXTmCWkKF9N4hSkwT1z8CKtgrMoMKX58xF4SARjgOZW+fS3u+69
k5SmTYKzAgMBAAECggEAI7eVKrfdjMkX9TmQdZjkWk6QbN2luJBIRdxwPKM0ZIpe
bQMIgfAGfaBXjL6cads4hb3TDLvCF/7ln05Rq9AmAR6WMDOiVM2W9W4PLf/XsbJY
9klVNcXyXnoXRvtbOtjm1MXOETt8Z4pOwguySDZhdH4rSszXkYgnM/1IdXhBzqCb
M890MbRzqokfWFvfFL9krRJqjxWsLXQ3aPVolBYDQ3o3T8e9X1KFtQtr0QMLkRR5
LlbWw9ZbnLis1fwDp54j1tJGVp1bHVrBOuNyhiBycQjzjvx62B8zLiKLcHHlBTGC
zKr083LwlJdiY+et2gSkuOOTgpp18AKP3b87W++I7QKBgQDpur29GY0OdqFilQrh
rtxPfoKIpNOS11YL6cxb9fqTjJtG2LD+WpRXZKFwgnk9s0apRGvKmalA3LdrRw1f
Ul9gI141lt1NtxNMN0a+r9s+SGO5Xi4K+UqeLML7iA9XKtvA/BeROQrXNLgd96Vj
JIfMJPU7FlYAJLwrmJNNAxSEtwKBgQDNn+yvfi3bpoPp7BJcy4pVlWSTP34rTGT5
Yoaf2jAnt7OEhoSWVMnEMY16QVdVCb3PaVozZ3SyZWOExGsUOxqZz1e2ruXsOCRi
UFwkBnNTI0Q+RvTdliWWtu/qdg+Q7kUKg2kML3P3wrqstrwlj6menWqn7tUTo6u9
GhOBcPaN5QKBgQDEZKFh78JS0OOyjkHieKeuNENCxhzxWfd3czDAZOP0b0VaNmIi
l8Hl3Sy5+Sge7DEHsfJQ/uT1F4EXp1BZNEHn6lAS/31c++Q/OoM7X1D9+J2y+Kv/
lJFab4o3CJC7UcvtUOYMpL2zLx02MQzLTbq9kqBs0cvZuwRSLZY4M8pd6QKBgQCy
RycZ3Md7unqCtSgShnKw0y75L8J/XePqCM96Bt1bgj1F+K85+9dXoDLuvXovg5ur
GceX6+nUxm0rbnT8fGYK1ydQf4Ffdimth8jrfyA8A8amTDT/ba+3ZXLLkILcgIkh
nV/VrcrZFF9vYZvs4QsKN6eCZGMffPdopBQnVT6fNQKBgCAMFhtaV8lYuo2ZrdXw
SLrQ1fUPxQ8jQAT9cYsAmMvng9fDfPExJT4FYRAS/Fg86V2YADyhmgb3ODs1Zb7n
DtQqheLx15rdzk3p4rusC0/QR6jj/so7aQUGxxENVCF+M6+esmFmK4mU3KBRR7wE
Imp3da9c3VSuBQno2XNplUz7
-----END PRIVATE KEY-----"""
SENDER_PUBKEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu7yNBKauosSwVUdvB1jp
Y2xZy0voWg1iIme/t3ht9nfnmHfFtbTiFp9e+KnHu2qebBDPq2J/WnPPy68VfTrJ
9Kh4IHpBxarunsr4AQwt5kZLLgHmLFoOHS9fN6oO+Mkp06TbN9jw8MUR3A7pq3wD
4L4znbzjqeJYwvq4513Izu8fCakz4ISlfxvKSqsjPsa4tzQwExhpyZqzcRJ+hKHs
6ZE9to1okEfHtKJs/xEGIRmqXz1qzkCLkHXSlcTsuTHREY/ZoJ6aNkuzsk4L8P8M
zj9Rqkpl05glpChfTeIUpME9c/AirYKzKDCl+fMReEgEY4DmVvn0t7vuvZOUpk2C
swIDAQAB
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
            timeout=120
        )

        print("\n--- Response ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body:\n{response.text}")
        print("----------------\n")

        if response.status_code == 200:
            print("[SUCCESS] The request was successful!")
        else:
            print(f"[FAILURE] The request failed with status code {response.status_code}.")

    except requests.exceptions.RequestException as e:
        print("\n[FAILURE] The connection failed.")
        print(f"Error: {e}")

if __name__ == '__main__':
    run_test()
