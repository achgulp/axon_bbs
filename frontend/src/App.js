// Full path: axon_bbs/frontend/src/App.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from './apiClient';
import LoginScreen from './components/LoginScreen';
import RegisterScreen from './components/RegisterScreen';
import MessageList from './components/MessageList';
import UnlockForm from './components/UnlockForm';
import ProfileScreen from './components/ProfileScreen';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const SideBarButton = ({ onClick, children, className = '' }) => (
  <button onClick={onClick} className={`w-full text-left py-2 px-4 rounded hover:bg-gray-700 text-gray-300 transition duration-150 ease-in-out ${className}`}>
    {children}
  </button>
);
const MessageBoardList = ({ onSelectBoard }) => {
  const [boards, setBoards] = useState([]);
  useEffect(() => {
    apiClient.get('/api/boards/')
      .then(response => setBoards(response.data))
      .catch(err => console.error(err));
  }, []);
  return (
    <div>
      <Header text="Message Boards" />
      <div className="space-y-2">
        {boards.map(board => (
          <button
            key={board.id}
            onClick={() => onSelectBoard(board.id, board.name)}
            className="w-full text-left p-3 rounded bg-gray-800 hover:bg-gray-700 border border-gray-700"
          >
            <h3 className="font-bold text-gray-200">{board.name}</h3>
            <p className="text-sm text-gray-400">{board.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

const PrivateMessageClient = ({ setNeedsUnlock, initialRecipient = null }) => {
  const [inboxMessages, setInboxMessages] = useState([]);
  const [outboxMessages, setOutboxMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [view, setView] = useState('inbox');
  const [showCompose, setShowCompose] = useState(!!initialRecipient);
  
  const [recipientIdentifier, setRecipientIdentifier] = useState(initialRecipient ? initialRecipient.displayName : '');
  const [recipientPubkey, setRecipientPubkey] = useState(initialRecipient ? initialRecipient.pubkey : null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchMessages = useCallback(() => {
    setError('');
    const endpoint = view === 'inbox' ? '/api/pm/list/' : '/api/pm/outbox/';
    apiClient.get(endpoint)
      .then(response => {
        if (view === 'inbox') {
          setInboxMessages(response.data);
        } else {
          setOutboxMessages(response.data);
        }
      })
      .catch(err => {
        if (err.response && err.response.data.error === 'identity_locked') {
          setNeedsUnlock(true);
        } else {
          console.error(`Error fetching ${view}:`, err);
          setError(`Could not fetch ${view} messages.`);
        }
      });
  }, [setNeedsUnlock, view]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    if (!recipientIdentifier || !subject || !body) {
      setError("Recipient, subject, and body are required.");
      return;
    }
    try {
      const payload = { recipient_identifier: recipientIdentifier, recipient_pubkey: recipientPubkey, subject, body };
      await apiClient.post('/api/pm/send/', payload);
      setSuccess('Message sent successfully!');
      setRecipientIdentifier(''); setRecipientPubkey(null); setSubject(''); setBody('');
      setShowCompose(false);
      setView('outbox');
    } catch (err) {
      if (err.response && err.response.data.error === 'identity_locked') {
        setNeedsUnlock(true);
      } else {
        setError(err.response?.data?.error || 'Failed to send message.');
      }
    }
  };

  const handleForward = () => {
    if (!selectedMessage) return;
    setSubject(`Fwd: ${selectedMessage.subject}`);
    const forwardHeader = `\n\n--- Forwarded Message ---\nTo: ${selectedMessage.recipient_display}\nSubject: ${selectedMessage.subject}\n\n`;
    setBody(forwardHeader + selectedMessage.decrypted_body);
    setSelectedMessage(null);
    setShowCompose(true);
    setRecipientIdentifier('');
    setRecipientPubkey(null);
  };

  if (selectedMessage) {
    const isInbox = view === 'inbox';
    const displayName = isInbox ? selectedMessage.author_display : selectedMessage.recipient_display;
    const avatarUrl = isInbox ? selectedMessage.author_avatar_url : selectedMessage.recipient_avatar_url;

    return (
      <div>
        <button onClick={() => setSelectedMessage(null)} className="mb-4 bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
          ← Back to {isInbox ? 'Inbox' : 'Outbox'}
        </button>
        {!isInbox && (
          <button onClick={handleForward} className="mb-4 ml-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Forward
          </button>
        )}
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <h3 className="text-xl font-bold text-white mb-1">{selectedMessage.subject}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
            <img src={avatarUrl || '/default_avatar.png'} alt="avatar" className="w-6 h-6 rounded-full bg-gray-700" />
            <span>{isInbox ? `From: ${displayName}` : `To: ${displayName}`} on {new Date(selectedMessage.created_at).toLocaleString()}</span>
          </div>
          <p className="text-gray-300 whitespace-pre-wrap mb-4">{selectedMessage.decrypted_body}</p>
        </div>
      </div>
    );
  }

  const messages = view === 'inbox' ? inboxMessages : outboxMessages;
  const columns = view === 'inbox'
    ? { id: 'From', value: msg => msg.author_display, avatar: msg => msg.author_avatar_url }
    : { id: 'To', value: msg => msg.recipient_display, avatar: msg => msg.recipient_avatar_url };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <Header text="Private Mail" />
        <button onClick={() => { setShowCompose(!showCompose); setRecipientIdentifier(''); setRecipientPubkey(null); }} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          {showCompose ? 'Cancel' : 'Compose'}
        </button>
      </div>
      <div className="flex gap-2 mb-4 border-b border-gray-700">
        <button onClick={() => setView('inbox')} className={`py-2 px-4 ${view === 'inbox' ? 'text-white border-b-2 border-blue-500' : 'text-gray-400'}`}>Inbox</button>
        <button onClick={() => setView('outbox')} className={`py-2 px-4 ${view === 'outbox' ? 'text-white border-b-2 border-blue-500' : 'text-gray-400'}`}>Outbox</button>
      </div>
      {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
      {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>}
      {showCompose && (
        <div className="bg-gray-800 p-4 rounded mb-6 border border-gray-700">
          <form onSubmit={handleSendMessage}>
            <input type="text" placeholder="Recipient's Username or Nickname" value={recipientIdentifier} onChange={e => setRecipientIdentifier(e.target.value)} required className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <input type="text" placeholder="Subject" value={subject} onChange={e => setSubject(e.target.value)} required className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <textarea placeholder="Your encrypted message..." value={body} onChange={e => setBody(e.target.value)} required rows="5" className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <div className="text-right">
              <button type="submit" className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Send Message</button>
            </div>
          </form>
        </div>
      )}
      <div className="bg-gray-800 rounded border border-gray-700">
        <table className="w-full text-left table-auto">
          <thead className="border-b border-gray-600">
            <tr>
              <th className="p-3 text-sm font-semibold text-gray-400 w-3/5">Subject</th>
              <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">{columns.id}</th>
              <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">{view === 'inbox' ? 'Received' : 'Sent'}</th>
            </tr>
          </thead>
          <tbody>
            {messages.map(msg => (
              <tr key={msg.id} className="border-b border-gray-700 last:border-b-0 hover:bg-gray-700 cursor-pointer" onClick={() => setSelectedMessage(msg)}>
                <td className="p-3 text-gray-200">{msg.subject}</td>
                <td className="p-3 text-gray-400 flex items-center gap-2">
                  <img src={columns.avatar(msg) || '/default_avatar.png'} alt="avatar" className="w-8 h-8 rounded-full bg-gray-700" />
                  {columns.value(msg)}
                </td>
                <td className="p-3 text-gray-400">{new Date(msg.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {messages.length === 0 && <p className="text-gray-400 text-center p-4">Your {view} is empty.</p>}
      </div>
    </div>
  );
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [authView, setAuthView] = useState('login');
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [isIdentityUnlocked, setIdentityUnlocked] = useState(false);
  const [needsUnlock, setNeedsUnlock] = useState(false);
  const [currentView, setCurrentView] = useState('boards');
  const [pmRecipient, setPmRecipient] = useState(null);
  const setAuthToken = (newToken) => {
    if (newToken) {
      localStorage.setItem('token', newToken);
    } else {
      localStorage.removeItem('token');
      setIdentityUnlocked(false);
    }
    setToken(newToken);
  };
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);
  const handleLogout = async () => {
    try {
      await apiClient.post('/api/logout/');
    } catch (err) {
      console.error("Failed to clear server session, logging out client-side anyway.", err);
    } finally {
      setAuthToken(null);
    }
  };
  const handleSelectBoard = (boardId, boardName) => {
    setSelectedBoard({ id: boardId, name: boardName });
    setCurrentView('boards');
  };
  const handleViewChange = (view) => {
    setSelectedBoard(null);
    setPmRecipient(null);
    setCurrentView(view);
  };
  const handleStartPrivateMessage = (pubkey, displayName) => {
    setPmRecipient({ pubkey: pubkey, displayName: displayName });
    setCurrentView('pm');
  };
  const handleUnlockSuccess = () => {
    setIdentityUnlocked(true);
    setNeedsUnlock(false);
  };
  if (!token) {
    return (
      <div className="bg-gray-800 min-h-screen">
        {authView === 'login' ? (
          <LoginScreen onLogin={setAuthToken} onNavigateToRegister={() => setAuthView('register')} />
        ) : (
          <RegisterScreen onRegisterSuccess={() => setAuthView('login')} onNavigateToLogin={() => setAuthView('login')} />
        )}
      </div>
    );
  }

  const renderMainContent = () => {
    if (currentView === 'profile') {
      return <ProfileScreen />;
    }
    if (currentView === 'pm') {
      return <PrivateMessageClient setNeedsUnlock={setNeedsUnlock} initialRecipient={pmRecipient} />;
    }
    
    if (selectedBoard) {
      return <MessageList board={selectedBoard} onBack={() => setSelectedBoard(null)} onStartPrivateMessage={handleStartPrivateMessage} />;
    }
    return <MessageBoardList onSelectBoard={handleSelectBoard} />;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-300 font-sans">
      {needsUnlock && <UnlockForm onUnlock={handleUnlockSuccess} onCancel={() => setNeedsUnlock(false)} />}

      <div className="flex flex-col md:flex-row">
        <div className="w-full md:w-60 bg-gray-800 p-4 border-r border-gray-700 flex-shrink-0">
          <div className="flex items-center text-2xl font-bold text-white mb-6">
            <img src="/axon.png" alt="Axon logo" className="h-12 w-12 mr-3"/>
            <h2>Axon BBS</h2>
          </div>
          <nav className="space-y-2">
            <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">Menu</h3>
              <SideBarButton onClick={() => handleViewChange('boards')}>Message Boards</SideBarButton>
              <SideBarButton onClick={() => handleViewChange('pm')}>Private Mail</SideBarButton>
            </div>
            <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">User</h3>
              <SideBarButton
                onClick={() => setNeedsUnlock(true)}
                className={isIdentityUnlocked ? 'text-green-400' : 'text-yellow-400'}
              >
                {isIdentityUnlocked ? '✓ Identity Unlocked' : '✗ Unlock Identity'}
              </SideBarButton>
              <SideBarButton onClick={() => handleViewChange('profile')}>Profile</SideBarButton>
              <SideBarButton onClick={handleLogout}>Logout</SideBarButton>
            </div>
          </nav>
        </div>
        <main className="flex-1 p-6">
          {renderMainContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
