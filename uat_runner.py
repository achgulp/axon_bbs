# Axon BBS - A modern, anonymous, federated bulletin board system.
# Copyright (C) 2025 Achduke7
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; #
# without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


# Full path: axon_bbs/uat_runner.py
import requests
import time
import os
import json
import base64
from uuid import uuid4
from dotenv import load_dotenv
from PIL import Image
import io

# --- CONFIGURATION ---
load_dotenv()
HOST_BBS_ONION = os.getenv("ONION_ADDRESS")
TOR_PROXIES = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

if not HOST_BBS_ONION:
    raise ValueError("Please set ONION_ADDRESS in your .env file")
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
        url = f"http://{HOST_BBS_ONION}{endpoint}"
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

def test_get_self_profile(client):
    response = client._request('GET', '/api/user/profile/')
    if response.status_code != 200:
        raise Exception(f"Failed to get user profile. Status: {response.status_code}, Body: {response.text}")
    return response.json()

def test_upload_file(client, filename, content):
    file_content = io.BytesIO(content.encode('utf-8'))
    files = {'file': (filename, file_content, 'text/plain')}
    response = client._request('POST', '/api/files/upload/', files=files)
    if response.status_code != 201:
        raise Exception(f"File upload failed. Status: {response.status_code}, Body: {response.text}")
    
    response_data = response.json()
    return {"id": response_data['id'], "content": content}

def test_post_message_with_attachment(client, board_name, subject, body, attachment_id):
    payload = {"board_name": board_name, "subject": subject, "body": body, "attachment_ids": [attachment_id]}
    response = client._request('POST', '/api/messages/post/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Post message failed. Status: {response.status_code}, Body: {response.text}")
    
    response_data = response.json()
    # --- FIX START ---
    # The API returns 'message_id', not 'id'.
    return {"message_id": response_data['message_id'], "subject": subject}
    # --- FIX END ---

def test_report_message(client, message_id, comment):
    payload = {"message_id": message_id, "comment": comment}
    response = client._request('POST', '/api/messages/report/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to report message. Status: {response.status_code}, Body: {response.text}")
    return f"Successfully reported message ID {message_id}."

def test_upload_avatar(client):
    img = Image.new('RGB', (60, 30), color = 'red')
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    files = {'avatar': ('test_avatar.png', buffer, 'image/png')}
    response = client._request('POST', '/api/user/avatar/', files=files)
    if response.status_code != 200:
        raise Exception(f"Avatar upload failed. Status: {response.status_code}, Body: {response.text}")
    return "Avatar submitted for approval."

def test_send_pm(client, recipient, subject, body):
    payload = {"recipient_identifier": recipient, "subject": subject, "body": body}
    response = client._request('POST', '/api/pm/send/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Send PM failed. Status: {response.status_code}, Body: {response.text}")
    return {"subject": subject, "body": body}

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

def test_post_log_to_uat_channel(client, log_content):
    payload = {
        "board_name": "UAT-Channel",
        "subject": "start_uat",
        "body": json.dumps(log_content, indent=2)
    }
    response = client._request('POST', '/api/messages/post/', json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to post log to UAT channel. Status: {response.status_code}, Body: {response.text}")
    return "UAT log posted to trigger verifier agent."

def test_verify_peer_attachment(client):
    # Get the original message ID
    log_entry = next((item for item in client.log if item['step'].startswith("5)")), None)
    if not (log_entry and log_entry['status'] == 'PASS'):
        raise Exception("Prerequisite step did not pass on host.")
    original_message_id = log_entry['details']['message_id']

    # Poll for the reply message
    for _ in range(15):
        time.sleep(10)
        response = client._request('GET', '/api/boards/3/messages/') # Assuming UAT-Channel is board 3
        if response.status_code == 200:
            messages = response.json()
            for message in messages:
                if message['parent'] == original_message_id:
                    attachment = message['attachments'][0]
                    # Download the attachment
                    response = client._request('GET', f'/api/files/download/{attachment["id"]}/', stream=True)
                    if response.status_code == 200:
                        if response.text == "This is the content of the attachment from the peer.":
                            return "Peer attachment verified successfully."
                        else:
                            raise Exception("Peer attachment content mismatch.")
                    else:
                        raise Exception(f"Failed to download peer attachment. Status: {response.status_code}, Body: {response.text}")
    raise Exception("Timed out waiting for peer attachment.")

def run_uat_suite(peer_onion_url):
    """Runs the full UAT test suite."""
    time.sleep(30)
    client = UATClient()
    
    # Generate unique credentials for this test run
    run_id = str(uuid4())[:8]
    USERNAME = f"uat_user_{run_id}"
    NICKNAME = f"UAT-Runner-{run_id}"
    PASSWORD_V1 = f"password_{run_id}_v1"
    PASSWORD_V2 = f"password_{run_id}_v2"
    
    try:
        # --- Execute Test Plan ---
        client.run_test("0) Register New User", test_register, client, USERNAME, PASSWORD_V1, NICKNAME)
        client.run_test("1) Login", test_login, client, USERNAME, PASSWORD_V1)
        client.run_test("2) Unlock Identity", test_unlock_identity, client, PASSWORD_V1)
        profile = client.run_test("3) Get Self Profile", test_get_self_profile, client)
        
        attachment_content = f"This is a test file for UAT run {run_id}."
        attachment_result = client.run_test("4) Upload Attachment", test_upload_file, client, f"uat_file_{run_id}.txt", attachment_content)

        post_subject = f"UAT Post from {NICKNAME}"
        post_result = client.run_test("5) Create Message with Attachment", test_post_message_with_attachment, client, "Tech", post_subject, "This is a UAT test message with an attachment.", attachment_result['id'])
        
        pm_subject = f"UAT PM from {NICKNAME}"
        pm_body = "This is a UAT private message."
        pm_result = client.run_test("6) Send PM to Peer BBS User", test_send_pm, client, "pibbs_user", pm_subject, pm_body)
        
        # Add the sender pubkey to the log for the verifier
        pm_result['sender_pubkey'] = profile['pubkey']

        # Create a second user to report the message
        run_id_2 = str(uuid4())[:8]
        USERNAME_2 = f"uat_user_2_{run_id_2}"
        NICKNAME_2 = f"UAT-Runner-2-{run_id_2}"
        PASSWORD_V1_2 = f"password_{run_id_2}_v1"
        client.run_test("7a) Register Second User", test_register, client, USERNAME_2, PASSWORD_V1_2, NICKNAME_2)
        client.run_test("7b) Login as Second User", test_login, client, USERNAME_2, PASSWORD_V1_2)
        client.run_test("7c) Unlock Identity of Second User", test_unlock_identity, client, PASSWORD_V1_2)
        client.run_test("7d) Report Message from Second User", test_report_message, client, post_result['message_id'], "This message is for UAT testing.")

        # Create a second user to report the message
        run_id_2 = str(uuid4())[:8]
        USERNAME_2 = f"uat_user_2_{run_id_2}"
        NICKNAME_2 = f"UAT-Runner-2-{run_id_2}"
        PASSWORD_V1_2 = f"password_{run_id_2}_v1"
        client.run_test("7a) Register Second User", test_register, client, USERNAME_2, PASSWORD_V1_2, NICKNAME_2)
        client.run_test("7b) Login as Second User", test_login, client, USERNAME_2, PASSWORD_V1_2)
        client.run_test("7c) Unlock Identity of Second User", test_unlock_identity, client, PASSWORD_V1_2)
        client.run_test("7d) Report Message from Second User", test_report_message, client, post_result['message_id'], "This message is for UAT testing.")

        
        new_nickname = f"UAT-Runner-{run_id}-Updated"
        client.run_test("8) Change Nickname", test_change_nickname, client, new_nickname)
        client.run_test("9) Upload Avatar", test_upload_avatar, client)
        
        client.run_test("9a) Login as First User", test_login, client, USERNAME, PASSWORD_V1)
        client.run_test("10) Change Password", test_change_password, client, PASSWORD_V1, PASSWORD_V2)
        client.run_test("11) Logout", test_logout, client)
        client.run_test("12) Log in with New Password", test_login, client, USERNAME, PASSWORD_V2)
        client.run_test("12a) Unlock Identity with New Password", test_unlock_identity, client, PASSWORD_V2)
        
        # Final step: Post the log to the UAT channel to trigger the verifier
        client.run_test("13) Trigger Verifier Agent", test_post_log_to_uat_channel, client, client.log)

        client.run_test("14) Verify Peer Attachment", test_verify_peer_attachment, client)

        print("\n[+] UAT RUNNER COMPLETED SUCCESSFULLY.")
        
    except Exception as e:
        print(f"\n[!] UAT FAILED. See log for details.")
    
    finally:
        client.save_log()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python uat_runner.py <peer_onion_url>")
        sys.exit(1)
    peer_url = sys.argv[1]
    run_uat_suite(peer_url)
