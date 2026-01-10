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


# Full path: axon_bbs/core/management/commands/rebuild_frontend.py
import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Installs frontend dependencies and builds the frontend application.'

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Frontend Rebuild Process ---")
        
        frontend_dir = os.path.join(settings.BASE_DIR, 'frontend')

        if not os.path.isdir(frontend_dir):
            self.stderr.write(self.style.ERROR(f"Frontend directory not found at: {frontend_dir}"))
            return

        # --- Step 1: Install npm dependencies ---
        self.stdout.write(self.style.NOTICE(f"Running 'npm install' in {frontend_dir}..."))
        try:
            install_process = subprocess.run(
                ['npm', 'install'],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
            self.stdout.write(self.style.SUCCESS("'npm install' completed successfully."))
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR("`npm` command not found. Is Node.js installed and in your PATH?"))
            return
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"'npm install' failed with return code {e.returncode}."))
            self.stderr.write(e.stderr)
            return

        # --- Step 2: Build the React application ---
        self.stdout.write(self.style.NOTICE("Running 'npm run build'..."))
        try:
            build_process = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
            self.stdout.write(self.style.SUCCESS("Frontend build completed successfully!"))
            self.stdout.write("Static files have been generated in the 'frontend/build' directory.")
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"'npm run build' failed with return code {e.returncode}."))
            # MODIFIED: Print the full stdout and stderr from the failed process
            self.stderr.write("\n--- NPM BUILD OUTPUT (stdout) ---\n")
            self.stderr.write(e.stdout)
            self.stderr.write("\n--- NPM BUILD OUTPUT (stderr) ---\n")
            self.stderr.write(e.stderr)
            return
