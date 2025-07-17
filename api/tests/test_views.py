# axon_bbs/api/tests/test_views.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from core.models import MessageBoard, Message, FileArea, UploadedFile, PrivateMessage
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

# -----------------------------------------------------------------------------
# Test Cases for User Auth API Views
# -----------------------------------------------------------------------------

class UserAuthAPITest(APITestCase):
    """
    Test suite for the User Registration and Login API views.
    """
    def setUp(self):
        self.register_url = reverse('user-register')
        self.login_url = reverse('user-login')
        self.profile_url = reverse('user-profile')
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
    Test suite for the Message Board and Message API views.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', sl=10)
        self.public_board = MessageBoard.objects.create(name='Public', required_sl=10)
        self.client.force_authenticate(user=self.user)

    def test_post_message_to_board(self):
        url = reverse('message-list-create', kwargs={'board_id': self.public_board.id})
        post_data = {'title': 'New Post', 'body': 'This is a new message.'}
        response = self.client.post(url, post_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Message.objects.filter(title='New Post').exists())

# -----------------------------------------------------------------------------
# Test Cases for File System API Views
# -----------------------------------------------------------------------------

class FileSystemAPITest(APITestCase):
    """
    Test suite for the File Area and File Upload API views.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password', sl=20)
        self.public_area = FileArea.objects.create(name='Public Files', required_sl_view=10, required_sl_upload=20)
        self.client.force_authenticate(user=self.user)

    def test_file_upload_success(self):
        url = reverse('file-list-upload', kwargs={'area_id': self.public_area.id})
        dummy_file = SimpleUploadedFile("testfile.txt", b"file_content", content_type="text/plain")
        upload_data = {'description': 'A test file', 'file_content': dummy_file}
        response = self.client.post(url, upload_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UploadedFile.objects.filter(filename='testfile.txt').exists())

# -----------------------------------------------------------------------------
# Test Cases for Private Mail API Views
# -----------------------------------------------------------------------------

class PrivateMailAPITest(APITestCase):
    """
    Test suite for the Private Mail API views.
    """
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')
        
        # Authenticate as user1 by default
        self.client.force_authenticate(user=self.user1)

        # URL for listing/creating mail
        self.mail_url = reverse('private-message-list-create')

    def test_send_private_message(self):
        """
        Ensure a user can send a private message to another user.
        """
        mail_data = {
            'recipient': 'user2',
            'title': 'Hello!',
            'body': 'This is a test private message.'
        }
        response = self.client.post(self.mail_url, mail_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify the message exists in the database
        self.assertTrue(PrivateMessage.objects.filter(sender=self.user1, recipient=self.user2).exists())

    def test_list_inbox(self):
        """
        Ensure a user can list messages in their inbox.
        """
        # user1 sends a message to user2
        PrivateMessage.objects.create(sender=self.user1, recipient=self.user2, title='Hi', body='...')
        
        # Authenticate as user2 to check their inbox
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.mail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Hi')

    def test_list_sent_box(self):
        """
        Ensure a user can list messages in their sent box.
        """
        # user1 sends a message to user2
        PrivateMessage.objects.create(sender=self.user1, recipient=self.user2, title='Hi', body='...')
        
        # As user1, check the sent box
        response = self.client.get(self.mail_url + '?box=sent')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Hi')

    def test_read_message_marks_as_read(self):
        """
        Ensure viewing a message detail marks it as read for the recipient.
        """
        message = PrivateMessage.objects.create(sender=self.user1, recipient=self.user2, title='Unread', body='...')
        self.assertIsNone(message.read_at)

        # Authenticate as the recipient (user2)
        self.client.force_authenticate(user=self.user2)
        
        # URL for the specific message
        detail_url = reverse('private-message-detail', kwargs={'pk': message.id})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the message from the database and check the read_at field
        message.refresh_from_db()
        self.assertIsNotNone(message.read_at)


