# Axon BBS Developer Handbook

**Version**: 10.27.0+
**Last Updated**: October 23, 2025

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Coding Standards](#coding-standards)
5. [Development Workflows](#development-workflows)
6. [Testing](#testing)
7. [Database Management](#database-management)
8. [Frontend Development](#frontend-development)
9. [Backend Development](#backend-development)
10. [Applet Development](#applet-development)
11. [Debugging](#debugging)
12. [Git Workflow](#git-workflow)
13. [Deployment](#deployment)
14. [Common Tasks](#common-tasks)
15. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** (`python --version`)
- **Node.js 16+** (`node --version`)
- **PostgreSQL 12+** (`psql --version`)
- **Git** (`git --version`)
- **Tor** (optional, for federation testing)

### Quick Setup (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/axon_bbs.git
cd axon_bbs

# 2. Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Database setup
createdb axon_bbs_dev
python manage.py migrate
python manage.py createsuperuser

# 4. Frontend setup
cd frontend
npm install
npm run build
cd ..

# 5. Initialize BBS
python manage.py init_bbs_identity

# 6. Run development server
python manage.py runserver
```

Visit `http://localhost:8000` and log in with your superuser credentials.

---

## Development Environment Setup

### Python Virtual Environment

Always use a virtual environment to isolate dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate
deactivate
```

### Database Setup (PostgreSQL)

**Development Database:**
```bash
# Create database
createdb axon_bbs_dev

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://localhost/axon_bbs_dev
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# Run migrations
python manage.py migrate
```

**Test Database:**
```bash
# Django automatically creates test_axon_bbs_dev for tests
python manage.py test
```

### Frontend Development Setup

```bash
cd frontend

# Install dependencies
npm install

# Development server (hot reload)
npm start
# Opens http://localhost:3000 with proxy to Django backend

# Production build
npm run build
# Outputs to frontend/build/
```

### IDE Setup

**VS Code** (Recommended):
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

**Extensions:**
- Python (ms-python.python)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Django (batisteo.vscode-django)

**PyCharm:**
- Set Python interpreter to `venv/bin/python`
- Enable Django support: Settings → Languages & Frameworks → Django
- Set Django project root: `/path/to/axon_bbs`
- Set Settings: `axon_project/settings.py`

---

## Project Structure

```
axon_bbs/
├── core/                       # Core cross-cutting concerns
│   ├── models.py              # User, TrustedInstance, FileAttachment
│   ├── services/              # BitSyncService, SyncService, CryptoService
│   ├── views/                 # Core API endpoints
│   └── management/commands/   # CLI tools
│
├── accounts/                   # User account management
│   ├── models.py              # IgnoredPubkey, BannedPubkey
│   └── views.py               # Profile, authentication
│
├── messaging/                  # Message boards and messages
│   ├── models.py              # MessageBoard, Message, PrivateMessage
│   ├── services/              # RealtimeMessageService
│   ├── views.py               # Board and message APIs
│   └── serializers.py         # DRF serializers
│
├── applets/                    # Applet framework
│   ├── models.py              # Applet, AppletData, HighScore
│   ├── views.py               # Applet APIs
│   └── serializers.py         # Applet serializers
│
├── federation/                 # Inter-server communication
│   ├── models.py              # FederatedAction
│   ├── views.py               # Federation endpoints
│   └── services/              # FederationService
│
├── frontend/                   # React single-page application
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── AppletRunner.js
│   │   │   ├── MessageList.js
│   │   │   └── ...
│   │   ├── applets/           # Applet implementations
│   │   │   ├── AxonChat.js
│   │   │   ├── HexGL.js
│   │   │   └── FortressOverlord.js
│   │   ├── apiClient.js       # Axios configuration
│   │   └── App.js             # Main React component
│   └── public/
│
├── axon_project/               # Django project settings
│   ├── settings.py            # Django configuration
│   ├── urls.py                # URL routing
│   └── wsgi.py                # WSGI application
│
├── docs/                       # Documentation
├── logs/                       # Application logs
├── media/                      # Uploaded files (avatars, etc.)
├── staticfiles/                # Collected static files
├── manage.py                   # Django management script
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (local, not committed)
└── .gitignore                  # Git ignore rules
```

---

## Coding Standards

### Python (Backend)

**Style Guide**: PEP 8

**Formatter**: Black
```bash
pip install black
black .
```

**Linter**: Flake8
```bash
pip install flake8
flake8 .
```

**Import Order**:
```python
# 1. Standard library
import os
import json
from datetime import datetime

# 2. Third-party
from django.db import models
from rest_framework.views import APIView

# 3. Local
from core.models import User
from core.services.bitsync_service import BitSyncService
```

**Naming Conventions**:
- Classes: `PascalCase` (e.g., `MessageBoard`, `BitSyncService`)
- Functions/methods: `snake_case` (e.g., `create_message`, `get_user_info`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`, `DEFAULT_CHUNK_SIZE`)
- Private methods: `_leading_underscore` (e.g., `_validate_signature`)

**Docstrings**:
```python
def create_encrypted_content(file, public_key):
    """
    Create BitSync manifest with encrypted content.

    Args:
        file: File-like object to encrypt
        public_key: RSA public key for encryption

    Returns:
        dict: BitSync manifest with content_hash and encrypted_aes_keys

    Raises:
        ValueError: If file is empty or public_key is invalid
    """
    pass
```

### JavaScript/React (Frontend)

**Style Guide**: Airbnb JavaScript Style Guide

**Formatter**: Prettier
```bash
npm install --save-dev prettier
npx prettier --write "src/**/*.js"
```

**Linter**: ESLint
```bash
npm install --save-dev eslint
npx eslint src/
```

**Component Structure**:
```javascript
// Functional component with hooks (preferred)
import React, { useState, useEffect } from 'react';

function MessageList({ boardId }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMessages();
  }, [boardId]);

  const fetchMessages = async () => {
    // Implementation
  };

  return (
    <div className="message-list">
      {/* JSX */}
    </div>
  );
}

export default MessageList;
```

**Naming Conventions**:
- Components: `PascalCase` (e.g., `MessageList`, `AppletRunner`)
- Functions: `camelCase` (e.g., `fetchMessages`, `handleSubmit`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)
- Files: Match component name (e.g., `MessageList.js`)

---

## Development Workflows

### Feature Development

1. **Create feature branch**
```bash
git checkout -b feature/user-uploaded-applets
```

2. **Backend changes**
```bash
# Create/modify models
python manage.py makemigrations
python manage.py migrate

# Write tests
python manage.py test applets.tests.test_upload

# Run server
python manage.py runserver
```

3. **Frontend changes**
```bash
cd frontend
npm start  # Hot reload development server
```

4. **Test changes**
- Manual testing in browser
- Unit tests: `python manage.py test`
- Frontend tests: `npm test`

5. **Commit and push**
```bash
git add .
git commit -m "Add user applet upload functionality"
git push origin feature/user-uploaded-applets
```

6. **Create pull request** on GitHub

### Bug Fix Workflow

1. **Reproduce the bug**
- Document steps to reproduce
- Check logs: `tail -f logs/bbs.log`

2. **Write failing test**
```python
# messaging/tests.py
def test_message_ordering():
    """Messages should be ordered chronologically"""
    # Test that fails before fix
```

3. **Fix the bug**
- Make minimal changes
- Ensure test passes

4. **Verify fix**
- Run all tests
- Manual verification

5. **Commit with descriptive message**
```bash
git commit -m "Fix message ordering in realtime boards

Messages were displaying in reverse chronological order.
Now sorted by created_at ascending (oldest first).

Fixes #123"
```

---

## Testing

### Backend Tests

**Run all tests:**
```bash
python manage.py test
```

**Run specific app tests:**
```bash
python manage.py test messaging
python manage.py test applets.tests.test_models
```

**Run with coverage:**
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Opens htmlcov/index.html
```

**Writing tests:**
```python
# messaging/tests.py
from django.test import TestCase
from core.models import User
from messaging.models import Message, MessageBoard

class MessageTestCase(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.board = MessageBoard.objects.create(
            name='Test Board'
        )

    def test_create_message(self):
        """Messages should be created with author"""
        message = Message.objects.create(
            board=self.board,
            author=self.user,
            subject='Test',
            body='Test message'
        )
        self.assertEqual(message.author, self.user)
        self.assertEqual(message.board, self.board)

    def test_message_timestamp(self):
        """Messages should have creation timestamp"""
        message = Message.objects.create(
            board=self.board,
            author=self.user,
            subject='Test',
            body='Test'
        )
        self.assertIsNotNone(message.created_at)
```

### Frontend Tests

**Run tests:**
```bash
cd frontend
npm test
```

**Run with coverage:**
```bash
npm test -- --coverage
```

**Writing tests:**
```javascript
// src/components/MessageList.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import MessageList from './MessageList';

describe('MessageList', () => {
  test('renders loading state initially', () => {
    render(<MessageList boardId="123" />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('displays messages after loading', async () => {
    render(<MessageList boardId="123" />);
    await waitFor(() => {
      expect(screen.getByText(/test message/i)).toBeInTheDocument();
    });
  });
});
```

### Integration Tests

Test full workflows:

```python
# tests/integration/test_chat.py
from django.test import TestCase, Client
from core.models import User
from messaging.models import MessageBoard

class ChatIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.board = MessageBoard.objects.create(
            name='Chat',
            is_realtime=True
        )

    def test_post_and_read_message(self):
        """Full workflow: login, post message, read events"""
        # Login
        self.client.login(username='testuser', password='testpass123')

        # Post message
        response = self.client.post('/api/chat/post/', {
            'text': 'Hello, world!'
        })
        self.assertEqual(response.status_code, 200)

        # Read events
        response = self.client.get(
            f'/api/applets/{self.board.id}/read_events/'
        )
        self.assertEqual(response.status_code, 200)
        events = response.json()['events']
        self.assertEqual(len(events), 1)
        self.assertIn('Hello, world!', events[0]['body'])
```

---

## Database Management

### Migrations

**Create migration:**
```bash
python manage.py makemigrations
# Creates migration file in app/migrations/
```

**Apply migrations:**
```bash
python manage.py migrate
```

**View migration SQL:**
```bash
python manage.py sqlmigrate messaging 0001
```

**Rollback migration:**
```bash
python manage.py migrate messaging 0005
# Rolls back to migration 0005
```

**Reset migrations (DANGEROUS):**
```bash
# Delete all migrations
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Recreate
python manage.py makemigrations
python manage.py migrate --fake-initial
```

### Database Shell

**Django ORM shell:**
```bash
python manage.py shell
```

```python
>>> from core.models import User
>>> from messaging.models import Message
>>>
>>> # Query examples
>>> User.objects.all()
>>> User.objects.filter(is_moderator=True)
>>> Message.objects.filter(board__name='AxonChat').count()
>>>
>>> # Create objects
>>> user = User.objects.create_user(username='alice', password='pass')
>>>
>>> # Raw SQL (avoid when possible)
>>> from django.db import connection
>>> with connection.cursor() as cursor:
...     cursor.execute("SELECT COUNT(*) FROM messaging_message")
...     row = cursor.fetchone()
```

**PostgreSQL shell:**
```bash
psql axon_bbs_dev
```

```sql
-- Useful queries
SELECT COUNT(*) FROM messaging_message;
SELECT * FROM core_user WHERE is_sysop = true;
SELECT board_id, COUNT(*) FROM messaging_message GROUP BY board_id;
```

### Database Backup/Restore

**Backup:**
```bash
pg_dump axon_bbs_dev > backup.sql
```

**Restore:**
```bash
psql axon_bbs_dev < backup.sql
```

---

## Frontend Development

### Component Development

**Create new component:**
```javascript
// src/components/UserProfile.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchUser();
  }, [userId]);

  const fetchUser = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/users/${userId}/`);
      setUser(response.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="user-profile">
      <h2>{user.nickname}</h2>
      <p>Karma: {user.karma}</p>
    </div>
  );
}

export default UserProfile;
```

### API Integration

**Configure API client:**
```javascript
// src/apiClient.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Styling

**Tailwind CSS (Preferred):**
```jsx
<div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
  <h2 className="text-xl font-bold text-white">Message Board</h2>
  <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">
    New Message
  </button>
</div>
```

**Inline styles (for dynamic values):**
```jsx
<div style={{
  width: `${progress}%`,
  backgroundColor: progress > 80 ? 'green' : 'orange'
}}>
  {progress}%
</div>
```

### State Management

**Local state (useState):**
```javascript
const [messages, setMessages] = useState([]);
const [loading, setLoading] = useState(false);
```

**Context API (for global state):**
```javascript
// src/contexts/AuthContext.js
import React, { createContext, useState, useContext } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const login = async (username, password) => {
    // Login logic
    setUser(userData);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('authToken');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
```

**Usage:**
```javascript
import { useAuth } from './contexts/AuthContext';

function Header() {
  const { user, logout } = useAuth();

  return (
    <div>
      {user && (
        <div>
          <span>Welcome, {user.nickname}</span>
          <button onClick={logout}>Logout</button>
        </div>
      )}
    </div>
  );
}
```

---

## Backend Development

### Creating a New API Endpoint

1. **Define model** (if needed):
```python
# applets/models.py
class HighScore(models.Model):
    applet = models.ForeignKey(Applet, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score']
```

2. **Create serializer**:
```python
# applets/serializers.py
from rest_framework import serializers
from .models import HighScore

class HighScoreSerializer(serializers.ModelSerializer):
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)

    class Meta:
        model = HighScore
        fields = ['id', 'applet', 'user', 'user_nickname', 'score', 'created_at']
        read_only_fields = ['id', 'created_at']
```

3. **Create view**:
```python
# applets/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import HighScore, Applet
from .serializers import HighScoreSerializer

class HighScoreListView(APIView):
    def get(self, request, applet_id):
        """Get top 10 high scores for applet"""
        scores = HighScore.objects.filter(
            applet_id=applet_id
        ).select_related('user')[:10]

        serializer = HighScoreSerializer(scores, many=True)
        return Response(serializer.data)

    def post(self, request, applet_id):
        """Submit a new high score"""
        try:
            applet = Applet.objects.get(id=applet_id)
        except Applet.DoesNotExist:
            return Response(
                {'error': 'Applet not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        data = {
            'applet': applet.id,
            'user': request.user.id,
            'score': request.data.get('score')
        }

        serializer = HighScoreSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

4. **Add URL route**:
```python
# applets/urls.py
from django.urls import path
from .views import HighScoreListView

urlpatterns = [
    path('applets/<uuid:applet_id>/highscores/', HighScoreListView.as_view()),
]
```

5. **Test the endpoint**:
```python
# applets/tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from core.models import User
from applets.models import Applet, HighScore

class HighScoreTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.applet = Applet.objects.create(name='Test Game')
        self.client.force_authenticate(user=self.user)

    def test_submit_high_score(self):
        response = self.client.post(
            f'/api/applets/{self.applet.id}/highscores/',
            {'score': 1000}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(HighScore.objects.count(), 1)

    def test_get_high_scores(self):
        HighScore.objects.create(
            applet=self.applet,
            user=self.user,
            score=1000
        )
        response = self.client.get(
            f'/api/applets/{self.applet.id}/highscores/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
```

### Service Layer Pattern

Keep views thin, business logic in services:

```python
# messaging/services/message_service.py
from messaging.models import Message
from core.services.bitsync_service import BitSyncService

class MessageService:
    @staticmethod
    def create_message(author, board, subject, body, attachments=None):
        """
        Create a message with attachments.

        Args:
            author: User creating the message
            board: MessageBoard to post to
            subject: Message subject
            body: Message body
            attachments: List of uploaded files

        Returns:
            Message: Created message instance
        """
        # Create message
        message = Message.objects.create(
            author=author,
            board=board,
            subject=subject,
            body=body,
            pubkey=author.pubkey
        )

        # Process attachments
        if attachments:
            for file in attachments:
                manifest = BitSyncService.create_encrypted_content(
                    file,
                    author.pubkey
                )
                FileAttachment.objects.create(
                    content_hash=manifest['content_hash'],
                    manifest=manifest,
                    message=message,
                    author=author
                )

        return message
```

**Use in view:**
```python
from messaging.services.message_service import MessageService

class CreateMessageView(APIView):
    def post(self, request):
        message = MessageService.create_message(
            author=request.user,
            board_id=request.data['board_id'],
            subject=request.data['subject'],
            body=request.data['body'],
            attachments=request.FILES.getlist('attachments')
        )
        return Response(MessageSerializer(message).data)
```

---

## Applet Development

### Development Workflow

1. **Write applet code locally**:
```javascript
// MyApplet.js
(async function() {
  const root = document.getElementById('applet-root');
  const userInfo = await window.bbs.getUserInfo();

  root.innerHTML = `
    <div>
      <h1>Hello, ${userInfo.nickname}!</h1>
    </div>
  `;
})();
```

2. **Test locally** (create test HTML):
```html
<!-- test_applet.html -->
<!DOCTYPE html>
<html>
<head>
  <title>Applet Test</title>
</head>
<body>
  <div id="applet-root"></div>
  <script>
    // Mock window.bbs API for local testing
    window.bbs = {
      getUserInfo: () => Promise.resolve({
        username: 'testuser',
        nickname: 'Test User',
        pubkey: 'abc123'
      }),
      getData: () => Promise.resolve(null),
      saveData: (data) => {
        console.log('Saved:', data);
        return Promise.resolve();
      }
    };
  </script>
  <script src="MyApplet.js"></script>
</body>
</html>
```

3. **Deploy to BBS**:
```bash
python manage.py post_applet_update \
  --applet-id <uuid> \
  --file MyApplet.js \
  --version v1.0
```

4. **Update manifest**:
```bash
python manage.py update_applet_manifests
```

5. **Test in production**:
- Navigate to applet in BBS
- Open browser DevTools
- Check for errors
- Enable debug mode if needed

### Debugging Applets

**Enable debug mode:**
```python
# In Django admin
applet.is_debug_mode = True
applet.save()
```

**Add debug console to applet**:
```javascript
function debugLog(message) {
  if (window.BBS_DEBUG_MODE !== true) return;
  const debugDialog = document.getElementById('debug-dialog');
  if (!debugDialog) return;
  const logEntry = document.createElement('div');
  const timestamp = new Date().toLocaleTimeString();
  logEntry.textContent = `[${timestamp}] ${message}`;
  debugDialog.appendChild(logEntry);
}

// Usage
debugLog('Applet loaded');
debugLog(`User: ${userInfo.nickname}`);
```

---

## Debugging

### Backend Debugging

**Django Debug Toolbar:**
```bash
pip install django-debug-toolbar

# settings.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

**Print debugging:**
```python
import logging
logger = logging.getLogger(__name__)

def my_view(request):
    logger.debug(f"Request data: {request.data}")
    logger.info(f"User: {request.user.username}")
    logger.warning("Deprecated API called")
    logger.error("Failed to process request")
```

**PDB debugger:**
```python
def my_view(request):
    import pdb; pdb.set_trace()  # Breakpoint
    # Debugger shell:
    # n - next line
    # s - step into
    # c - continue
    # p variable - print variable
    # q - quit
```

**VS Code debugging:**
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Django",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["runserver"],
      "django": true
    }
  ]
}
```

### Frontend Debugging

**React DevTools** (browser extension)
- Install from Chrome/Firefox store
- Inspect component hierarchy
- View props and state
- Profile performance

**Console debugging:**
```javascript
console.log('Data:', data);
console.error('Error:', error);
console.table(messages);  // Tabular data
console.time('fetch');
await fetchData();
console.timeEnd('fetch');  // Logs duration
```

**Network debugging:**
- Open DevTools → Network tab
- Filter by XHR/Fetch
- Inspect request/response
- Check headers and payload

---

## Git Workflow

### Branch Strategy

```
main (production)
  ├── develop (integration)
  │   ├── feature/user-uploads
  │   ├── feature/video-embed
  │   └── bugfix/chat-ordering
  └── hotfix/critical-security-fix
```

### Commit Messages

**Format:**
```
<type>: <short summary>

<optional body>

<optional footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```bash
git commit -m "feat: add user applet upload functionality"

git commit -m "fix: correct message ordering in realtime boards

Messages were displaying newest-first instead of oldest-first.
Fixed by reversing the queryset in read_events endpoint.

Fixes #123"

git commit -m "docs: update applet development guide with new API"

git commit -m "refactor: extract message service logic from views"
```

### Code Review Checklist

Before creating PR:
- [ ] All tests pass
- [ ] Code follows style guide
- [ ] New code has tests
- [ ] Documentation updated
- [ ] No debug code left in
- [ ] Migrations created (if needed)
- [ ] Frontend built successfully

---

## Deployment

See [ARCHITECTURE.md](ARCHITECTURE.md#deployment-architecture) for full deployment guide.

**Quick production deploy:**
```bash
# 1. Pull latest code
git pull origin main

# 2. Update backend
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input

# 3. Update frontend
cd frontend
npm install
npm run build
cd ..

# 4. Restart services
sudo systemctl restart axon-bbs
sudo systemctl restart nginx
```

---

## Common Tasks

### Create New App

```bash
python manage.py startapp myapp

# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS += ['myapp']
```

### Add Python Package

```bash
pip install package-name
pip freeze > requirements.txt
git add requirements.txt
git commit -m "chore: add package-name dependency"
```

### Add npm Package

```bash
cd frontend
npm install package-name
git add package.json package-lock.json
git commit -m "chore: add package-name dependency"
```

### Reset Database (Development Only)

```bash
dropdb axon_bbs_dev
createdb axon_bbs_dev
python manage.py migrate
python manage.py createsuperuser
python manage.py init_bbs_identity
```

### Generate Test Data

```bash
python manage.py shell
```

```python
from core.models import User
from messaging.models import MessageBoard, Message

# Create users
for i in range(10):
    User.objects.create_user(
        username=f'user{i}',
        password='testpass123',
        nickname=f'User {i}'
    )

# Create board
board = MessageBoard.objects.create(name='Test Board')

# Create messages
users = User.objects.all()
for i in range(50):
    Message.objects.create(
        board=board,
        author=users[i % len(users)],
        subject=f'Test Message {i}',
        body=f'This is test message number {i}'
    )
```

---

## Troubleshooting

### Common Issues

**"Port 8000 already in use":**
```bash
lsof -ti:8000 | xargs kill -9
# Or use different port
python manage.py runserver 8001
```

**"ModuleNotFoundError":**
```bash
# Ensure venv is activated
source venv/bin/activate
pip install -r requirements.txt
```

**"No such table" error:**
```bash
python manage.py migrate
```

**Frontend won't start:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

**Migration conflicts:**
```bash
# If migrations are conflicting
python manage.py migrate --fake app_name migration_name
# Or delete conflicting migrations and recreate
```

**Database connection refused:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### Debug Checklist

Problem not solved?
1. Check logs: `tail -f logs/bbs.log`
2. Check Django settings: `DEBUG=True` in `.env`
3. Check database: `python manage.py dbshell`
4. Check migrations: `python manage.py showmigrations`
5. Check processes: `ps aux | grep python`
6. Clear cache: `python manage.py clear_cache`
7. Restart everything:
   ```bash
   sudo systemctl restart postgresql
   python manage.py runserver
   ```

---

## Resources

- **Django Documentation**: https://docs.djangoproject.com/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **React Documentation**: https://react.dev/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **PostgreSQL Manual**: https://www.postgresql.org/docs/

---

## Getting Help

- **Documentation**: Check `/docs` folder
- **Logs**: `tail -f logs/bbs.log`
- **GitHub Issues**: Open an issue with details
- **Code Comments**: Look for inline documentation
- **Tests**: Read test files for usage examples

---

**Last Updated**: October 23, 2025 by Achduke7

**Contributions**: See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
