# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY;
# without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.
# If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/uat_verifier.py
import os
import sys
import django
import time
import json
import requests

# --- CONFIGURATION ---
HOST_BBS_ONION = "http://YOUR_HOST_BBS.onion" # Must match the runner's config
TOR_PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'httpss': 'socks5h://127.0.0.1:9050'
}
# --- END CONFIGURATION ---

# --- Django Setup ---
def setup_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
    try:
        django.setup()
    except Exception as e:
        print(f"Error setting up Django: {e}")
        sys.exit(1)

setup_django()
from core.models import Message, PrivateMessage, User, Alias
# --- End Django Setup ---

def fetch_uat_log():
    """Fetches the UAT log from the host BBS."""
    # In a real-world scenario, this might be an authenticated endpoint.
    # For simplicity, we assume the log is accessible.
    # This endpoint does not exist yet; it's a conceptual part of the verifier.
    # For now, we will read it from a local file copied from the host.
    log_path = 'uat_results/uat_run_log.json' # Assumes the log was copied here
    print(f"[*] Reading UAT log from '{log_path}'...")
    try:
        with open(log_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[!] ERROR: UAT log file not found at '{log_path}'.")
        print("    Please run the UAT Runner on the host and copy the results here.")
        sys.exit(1)

def verify_public_post(run_log):
    """Verify that the public message from step 3 exists."""
    print("[*] Verifying Step 3: Public Message...")
    log_entry = next((item for item in run_log if item['step'].startswith("3)")), None)
    if not (log_entry and log_entry['status'] == 'PASS'):
        return "FAIL: Prerequisite step did not pass on host."

    subject = log_entry['details'].split("'")[1]
    if Message.objects.filter(subject=subject).exists():
        return "PASS"
    else:
        return f"FAIL: Could not find message with subject '{subject}'."

def verify_private_message(run_log):
    """Verify that the private message from step 5 exists."""
    print("[*] Verifying Step 5: Private Message...")
    log_entry = next((item for item in run_log if item['step'].startswith("5)")), None)
    if not (log_entry and log_entry['status'] == 'PASS'):
        return "FAIL: Prerequisite step did not pass on host."

    # We can't read the PM content, but we can check if a PM was received
    # around the time of the test for the target user.
    recipient = User.objects.get(nickname__iexact="pibbs_user")
    if PrivateMessage.objects.filter(recipient=recipient).exists():
        # This is a basic check. A more advanced check would look at timestamps.
        return "PASS"
    else:
        return "FAIL: No private message was received for user 'pibbs_user'."

def verify_nickname_federation(run_log):
    """Verify that the nickname change from step 12 was federated."""
    print("[*] Verifying Step 12: Nickname Federation...")
    log_entry = next((item for item in run_log if item['step'].startswith("12)")), None)
    if not (log_entry and log_entry['status'] == 'PASS'):
        return "FAIL: Prerequisite step did not pass on host."

    new_nickname = log_entry['details'].split("'")[1]
    # The federated user record should be an inactive User or an Alias
    if User.objects.filter(nickname__iexact=new_nickname, is_active=False).exists() or \
       Alias.objects.filter(nickname__iexact=new_nickname).exists():
        return "PASS"
    else:
        return f"FAIL: Could not find federated user/alias for nickname '{new_nickname}'."

if __name__ == "__main__":
    print("--- Axon BBS UAT Verifier ---")
    print("This script should be run on the PiBBS after the UAT Runner has completed on the host.")
    
    # Allow some time for federation to occur
    wait_time = 60
    print(f"\n[*] Waiting {wait_time} seconds for federation sync to complete...")
    time.sleep(wait_time)

    run_log = fetch_uat_log()
    results = []

    results.append(verify_public_post(run_log))
    results.append(verify_private_message(run_log))
    results.append(verify_nickname_federation(run_log))

    print("\n--- UAT VERIFICATION RESULTS ---")
    final_status = "PASS"
    for i, result in enumerate(results):
        print(f"  - Check {i+1}: {result}")
        if "FAIL" in result:
            final_status = "FAIL"
    
    print(f"\n[!] FINAL UAT STATUS: {final_status}")
