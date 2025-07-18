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
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='test@example.com'
        )

    def test_user_creation(self):
        """
        Test that a user can be created successfully.
        """
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpassword123'))
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
