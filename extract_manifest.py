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


# Full path: axon_bbs/extract_manifest.py
import os
import sys
import django
import json

# --- Django Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from core.models import Message, FileAttachment
# --- End Django Setup ---

def extract_manifest():
    """
    Finds all content with a manifest, displays a list, and prints
    the manifest of the user's selection in a readable JSON format.
    """
    print("--- Manifest Extraction Tool ---")
    
    try:
        # 1. Find all available content and display a list
        print("\n[1] Searching for available content in the database...")
        messages = Message.objects.filter(manifest__isnull=False)
        files = FileAttachment.objects.filter(manifest__isnull=False)
        all_content = list(messages) + list(files)

        if not all_content:
            print("   - No content with manifests found in the database.")
            return

        print(f"   - Found {len(all_content)} item(s):")
        for i, item in enumerate(all_content):
            content_type = "Message" if isinstance(item, Message) else "File"
            name = item.subject if isinstance(item, Message) else item.filename
            hash_short = item.manifest.get('content_hash', 'N/A')[:12]
            print(f"  [{i+1}] {content_type}: '{name}' (hash: {hash_short}...)")

        # 2. Get user input
        choice = input("\nEnter the number of the item to inspect: ")
        selected_index = int(choice) - 1

        if not (0 <= selected_index < len(all_content)):
            print("Invalid selection.")
            return

        selected_item = all_content[selected_index]
        manifest = selected_item.manifest
        
        print("\n--- ✅ Manifest for Selected Item ---")
        print(json.dumps(manifest, indent=2))
        print("--- End of Manifest ---")

    except Exception as e:
        print(f"\n--- ❌ An error occurred ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_manifest()
