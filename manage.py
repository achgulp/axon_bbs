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


# Full path: axon_bbs/manage.py

#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path # <-- ADD THIS LINE

# --- Application Version ---
APP_VERSION = "10.5.0"

def main():
    """Run administrative tasks."""
    # --- ADD THIS BLOCK TO AUTOMATICALLY CREATE DIRECTORIES ---
    BASE_DIR = Path(__file__).resolve().parent
    REQUIRED_DIRS = [
        BASE_DIR / 'logs',
        BASE_DIR / 'data',
    ]
    for path in REQUIRED_DIRS:
        os.makedirs(path, exist_ok=True)
    # --- END OF BLOCK TO ADD ---

    if os.environ.get('RUN_MAIN') != 'true':
        print(f"--- Axon BBS Management Utility v{APP_VERSION} ---")
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axon_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    is_runserver = 'runserver' in sys.argv
    is_reloader = os.environ.get('RUN_MAIN') == 'true'

    if is_runserver and not is_reloader:
       
        print("Starting development server at http://127.0.0.1:8000/")
        print("Admin site available at http://127.0.0.1:8000/admin/")

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
