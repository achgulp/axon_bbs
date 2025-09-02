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


# Full path: axon_bbs/core/services/content_validator.py
import magic
import logging
from core.models import ValidFileType

logger = logging.getLogger(__name__)

def is_file_type_valid(file_data: bytes) -> bool:
    """
    Checks the magic numbers of file data against a list of valid MIME types.

    :param file_data: The raw bytes of the decrypted file.
    :return: True if the file type is in the allowed list, False otherwise.
    """
    try:
        # Get the list of allowed MIME types from the database.
        allowed_mime_types = ValidFileType.objects.filter(is_enabled=True).values_list('mime_type', flat=True)
        
        if not allowed_mime_types:
            logger.warning("No valid file types are configured in the admin panel. Allowing all files by default.")
            return True

        # Detect the MIME type from the file's magic numbers.
        detected_mime_type = magic.from_buffer(file_data, mime=True)
        
        logger.info(f"Detected file MIME type: {detected_mime_type}")

        # Check if the detected type is in the allowed list.
        if detected_mime_type in allowed_mime_types:
            logger.info(f"File type '{detected_mime_type}' is valid.")
            return True
        else:
            logger.warning(f"Validation FAILED: File type '{detected_mime_type}' is not in the list of allowed types.")
            return False

    except Exception as e:
        logger.error(f"An error occurred during file type validation: {e}", exc_info=True)
        # Fail-safe: If an error occurs, block the file.
        return False
