#!/bin/bash
# Full path: axon_bbs/cleanup_refactor.sh
# This script removes files and directories made redundant by the Phase 3 backend refactoring.

# --- Configuration ---
# The base directory of your project. The script assumes it is run from the project root.
BASE_DIR="."
API_DIR="$BASE_DIR/api"

# --- Safety Check ---
# Make sure we are in the right place before deleting anything.
if [ ! -f "$BASE_DIR/manage.py" ] || [ ! -d "$API_DIR" ]; then
    echo "ERROR: This script must be run from the root of the 'axon_bbs' project directory."
    exit 1
fi

echo "--- Starting Refactor Cleanup ---"

# --- Files and Directories to be removed ---
FILE_TO_DELETE="$API_DIR/serializers.py"
DIR_TO_DELETE="$API_DIR/views"

# --- Deletion Process ---
# 1. Remove the old serializers file
if [ -f "$FILE_TO_DELETE" ]; then
    rm "$FILE_TO_DELETE"
    echo "SUCCESS: Deleted file: $FILE_TO_DELETE"
else
    echo "INFO: File already deleted: $FILE_TO_DELETE"
fi

# 2. Remove the old views directory
if [ -d "$DIR_TO_DELETE" ]; then
    rm -rf "$DIR_TO_DELETE"
    echo "SUCCESS: Deleted directory: $DIR_TO_DELETE"
else
    echo "INFO: Directory already deleted: $DIR_TO_DELETE"
fi

echo "--- Cleanup Complete ---"


