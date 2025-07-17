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

    def test_user_default_bbs_values(self):
        """
        Test that the custom BBS-specific fields are set to their
        correct default values upon user creation.
        """
        self.assertEqual(self.user.sl, 10)
        self.assertEqual(self.user.dsl, 10)
        self.assertEqual(self.user.uploads, 0)
        self.assertEqual(self.user.downloads, 0)
        self.assertEqual(self.user.uk, 0.0)
        self.assertEqual(self.user.dk, 0.0)
        self.assertEqual(self.user.msg_post, 0)
        self.assertEqual(self.user.email_sent, 0)
        self.assertEqual(self.user.time_today, 60)
        self.assertEqual(self.user.time_bank, 0)
        self.assertTrue(self.user.has_ansi)
        self.assertTrue(self.user.has_color)
        self.assertFalse(self.user.is_expert_menu)

    def test_string_representation(self):
        """
        Test the __str__ method of the User model.
        """
        self.assertEqual(str(self.user), 'testuser')

# --- We will add test cases for MessageBoard, Message, etc., here later ---

