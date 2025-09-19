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


# Full path: axon_bbs/uat_runner.py
import requests
import time
import os
import json
import base64
from uuid import uuid4

# --- CONFIGURATION ---
HOST_BBS_ONION = "http://YOUR_HOST_BBS.onion" # Replace with your Host BBS onion address
PIBBS_ONION = "http://YOUR_PIBBS.onion"       # Replace with your PiBBS onion address
TOR_PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'httpss': 'socks5h://127.0.0.1:9050'
}
# --- END CONFIGURATION ---

class UATClient:
    """A client to simulate a user interacting with the Axon BBS API for UAT."""

    def __init__(self):
        self.session = requests.Session()
        self.session.proxies = TOR_PROXIES
        self.access_token = None
        self.log = []

    def _request(self, method, endpoint, **kwargs):
        """Wrapper for making authenticated requests."""
        headers = kwargs.get("headers", {})
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        kwargs["headers"] = headers
        url = f"{HOST_BBS_ONION}{endpoint}"
        return self.session.request(method, url, **kwargs)

    def run_test(self, description, func, *args, **kwargs):
        """Runs a test step, logs the result, and handles failures."""
        self.log.append({"step": description, "status": "PENDING"})
        print(f"[*] Running: {description}...")
        try:
            result = func(*args, **kwargs)
            self.log[-1].update({"status": "PASS", "details": result})
            print(f"    -> PASS")
            return result
        except Exception as e:
            self.log[-1].update({"status": "FAIL", "details": str(e)})
            print(f"    -> FAIL: {e}")
            self.save_log()
            raise

    def save_log(self):
        """Saves the test log to a file."""
        os.makedirs('uat_results', exist_ok=True)
        log_path = 'uat_results/uat_run_log.json'
        with open(log_path, 'w') as f:
            json.dump(self.log, f, indent=2)
        print(f"\n[!] Test log saved to {log_path}")

# --- Test Functions ---

def test_register(client, username, password, nickname):
    payload = {
        "username": username, "password": password, "nickname": nickname,
        "security_question_1": "Test Q1", "security_answer_1": "Test A1",
        "security_question_2": "Test Q2", "security_answer_2": "Test A2"
    }
    response = client._request('POST', '/api/register/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to register. Status: {response.status_code}, Body: {response.text}")
    return "User registered successfully."

def test_login(client, username, password):
    response = client._request('POST', '/api/token/', json={"username": username, "password": password})
    if response.status_code != 200:
        raise Exception(f"Login failed. Status: {response.status_code}, Body: {response.text}")
    client.access_token = response.json()['access']
    return "Logged in successfully."

def test_unlock_identity(client, password):
    response = client._request('POST', '/api/identity/unlock/', json={"password": password})
    if response.status_code != 200:
        raise Exception(f"Identity unlock failed. Status: {response.status_code}, Body: {response.text}")
    return "Identity unlocked."

def test_post_message_with_attachment(client, board_name, subject, body):
    # This is a simplified test; it doesn't actually upload a file but uses the API structure.
    # A full test would require a multipart file upload endpoint. For now, we pass an empty list.
    payload = {"board_name": board_name, "subject": subject, "body": body, "attachment_ids": []}
    response = client._request('POST', '/api/messages/post/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Post message failed. Status: {response.status_code}, Body: {response.text}")
    return f"Message '{subject}' posted to '{board_name}'."

def test_send_pm(client, recipient, subject, body):
    payload = {"recipient_identifier": recipient, "subject": subject, "body": body}
    response = client._request('POST', '/api/pm/send/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Send PM failed. Status: {response.status_code}, Body: {response.text}")
    return f"PM '{subject}' sent to '{recipient}'."

def test_change_nickname(client, new_nickname):
    response = client._request('POST', '/api/user/nickname/', json={"nickname": new_nickname})
    if response.status_code != 200:
        raise Exception(f"Nickname change failed. Status: {response.status_code}, Body: {response.text}")
    return f"Nickname change to '{new_nickname}' submitted."
    
def test_change_password(client, old_password, new_password):
    payload = {"old_password": old_password, "new_password": new_password}
    response = client._request('POST', '/api/user/change_password/', json=payload)
    if response.status_code != 200:
        raise Exception(f"Password change failed. Status: {response.status_code}, Body: {response.text}")
    return "Password changed successfully."
    
def test_logout(client):
    response = client._request('POST', '/api/logout/')
    if response.status_code != 200:
        raise Exception("Logout failed.")
    client.access_token = None
    return "Logged out successfully."

if __name__ == "__main__":
    client = UATClient()
    
    # Generate unique credentials for this test run
    run_id = str(uuid4())[:8]
    USERNAME = f"uat_user_{run_id}"
    NICKNAME = f"UAT-Runner-{run_id}"
    PASSWORD_V1 = f"password_{run_id}_v1"
    PASSWORD_V2 = f"password_{run_id}_v2"
    
    # Define remote user for PM tests
    PIBBS_USER_NICKNAME = "pibbs_user" # Assume this user exists on the PiBBS

    try:
        # --- Execute Test Plan ---
        client.run_test("0) Register New User", test_register, client, USERNAME, PASSWORD_V1, NICKNAME)
        client.run_test("1) Login", test_login, client, USERNAME, PASSWORD_V1)
        client.run_test("2) Unlock Identity", test_unlock_identity, client, PASSWORD_V1)
        
        post_subject = f"UAT Post from {NICKNAME}"
        client.run_test("3) Create Message on Tech Board", test_post_message_with_attachment, client, "Tech", post_subject, "This is a UAT test message with an attachment.")
        
        pm_subject = f"UAT PM from {NICKNAME}"
        client.run_test("5) Send PM to PiBBS User", test_send_pm, client, PIBBS_USER_NICKNAME, pm_subject, "This is a UAT private message.")
        
        new_nickname = f"UAT-Runner-{run_id}-Updated"
        client.run_test("12) Change Nickname", test_change_nickname, client, new_nickname)
        
        client.run_test("14) Change Password", test_change_password, client, PASSWORD_V1, PASSWORD_V2)
        client.run_test("15) Logout", test_logout, client)
        client.run_test("16) Log in with New Password", test_login, client, USERNAME, PASSWORD_V2)
        
        print("\n[+] UAT RUNNER COMPLETED SUCCESSFULLY.")
        
    except Exception as e:
        print(f"\n[!] UAT FAILED. See log for details.")
    
    finally:
        client.save_log()
