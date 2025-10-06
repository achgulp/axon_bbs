#!/bin/bash
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


# Full path: axon_bbs/upgrade.sh
#
# This script is designed to upgrade an existing Axon BBS database schema
# to the latest version, accounting for the major refactoring of apps.
# It should be run from the root of the axon_bbs project directory.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Axon BBS Upgrade Process ---"

# Step 1: Activate virtual environment (adjust path if your venv is elsewhere)
echo "[1/5] Activating Python virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Warning: Could not find venv/bin/activate. Assuming environment is already active."
fi


# [cite_start]Step 2: Rename tables from the 'core' app to their new app names [cite: 536-541].
# This is a crucial step for databases created before the backend refactoring.
echo "[2/5] Renaming database tables to match new app structure..."
python3 manage.py rename_tables
echo "Table renaming complete."

# Step 3: Fake the initial migrations for the new apps.
# This tells Django that the tables for these apps already exist (because we just renamed them)
# and marks their initial migrations as "applied" without re-creating the tables.
echo "[3/5] Faking initial migrations for refactored apps..."
python3 manage.py migrate --fake-initial
echo "Initial migrations faked successfully."

# Step 4: Run any remaining migrations.
# This will apply any new schema changes that have been added since the initial migration,
# such as the new `SharedLibrary` model.
echo "[4/5] Applying any remaining database migrations..."
python3 manage.py migrate
echo "Database migration complete."

# Step 5: Collect static files for deployment.
echo "[5/5] Collecting static files..."
python3 manage.py collectstatic --no-input > /dev/null 2>&1
echo "Static files collected."

echo ""
echo "--- Axon BBS Upgrade Complete! ---"
echo "The database schema is now up to date with the latest code."
