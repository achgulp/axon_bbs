#!/bin/sh

# This script removes files and directories that are now obsolete after the
# Phase 4 service layer refactoring of the Axon BBS project.
# This version is POSIX-compliant to work with /bin/sh.

echo "--- Starting Axon BBS Refactor Cleanup ---"

# 1. Remove the entire 'api' directory
API_DIR="api"
if [ -d "$API_DIR" ]; then
    echo "Deleting obsolete directory: $API_DIR/"
    rm -rf "$API_DIR"
    echo " -> Done."
else
    echo " -> Directory $API_DIR/ not found, skipping."
fi

# 2. Define the list of obsolete service files in a space-separated string
OBSOLETE_SERVICES="\
core/services/avatar_generator.py \
core/services/high_score_service.py \
core/services/identity_service.py \
core/services/moderator_agent_service.py \
core/services/overlord_agent_service.py \
core/services/uat_verifier_agent_service.py"

# 3. Loop through the list and delete each file
echo "Deleting relocated service files from core/services/..."
for file in $OBSOLETE_SERVICES; do
    if [ -f "$file" ]; then
        echo " - Removing $file"
        rm "$file"
    else
        echo " - File $file not found, skipping."
    fi
done
echo " -> Done."

echo "--- Cleanup Complete ---"
