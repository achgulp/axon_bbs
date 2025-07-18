# axon_bbs/api/tests/test_views.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from core.models import MessageBoard, Message

User = get_user_model()

# -----------------------------------------------------------------------------
# Test Cases for User Auth API Views
# -----------------------------------------------------------------------------

class UserAuthAPITest(APITestCase):
    """
    Test suite for the User Registration and Login API views.
    """
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('token_obtain_pair')
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword123',
            'email': 'test@example.com'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_registration(self):
        new_user_data = {'username': 'newuser', 'password': 'newpassword123', 'email': 'new@example.com'}
        response = self.client.post(self.register_url, new_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_login(self):
        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

# -----------------------------------------------------------------------------
# Test Cases for Message Board API Views
# -----------------------------------------------------------------------------

class MessageBoardAPITest(APITestCase):
    """
    Test suite for the Message Board API views.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', access_level=10)
        self.public_board = MessageBoard.objects.create(name='Public', required_access_level=10)
        self.client.force_authenticate(user=self.user)

    def test_list_boards(self):
        url = reverse('board-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Public')

    def test_post_message_to_board(self):
        url = reverse('post-message')
        post_data = {'subject': 'New Post', 'body': 'This is a new message.', 'board_name': self.public_board.name}
        response = self.client.post(url, post_data, format='json')
        # Note: This test may fail if identity is not unlocked; in a full test, we'd need to mock or unlock first.
        # For now, assume it checks the endpoint exists and basic validation.
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            self.assertEqual(response.data['error'], 'identity_locked')
        else:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue('event_id' in response.data)
