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


# axon_bbs/core/tests/test_models.py

from django.test import TestCase
from django.contrib.auth import get_user_model

# Get the custom User model we defined
User = get_user_model()

# -----------------------------------------------------------------------------
# Test Cases for Core Models
# -----------------------------------------------------------------------------

class UserModelTest(TestCase):
    """
    Test suite for the custom User model.
    """

    def setUp(self):
        """
        Set up the test environment. This method is run before each test.
        We create a standard user instance here.
        """
        # --- CHANGE START ---
        # Define the password as a variable to avoid repetition and errors.
        self.test_password = 'a-secure-password-for-testing'
        self.user = User.objects.create_user(
            username='testuser',
            password=self.test_password,
            email='test@example.com'
        )
        # --- CHANGE END ---

    def test_user_creation(self):
        """
        Test that a user can be created successfully.
        """
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        # --- CHANGE START ---
        # Use the variable here to ensure the test is consistent.
        self.assertTrue(self.user.check_password(self.test_password))
        # --- CHANGE END ---
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_user_default_values(self):
        """
        Test that the custom fields are set to their
        correct default values upon user creation.
        """
        self.assertEqual(self.user.access_level, 10)
        self.assertFalse(self.user.is_banned)

    def test_string_representation(self):
        """
        Test the __str__ method of the User model.
        """
        self.assertEqual(str(self.user), 'testuser')

# --- We will add test cases for MessageBoard, Message, etc., here later ---
