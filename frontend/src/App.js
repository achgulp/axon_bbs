// Full path: axon_bbs/frontend/src/App.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from './apiClient';
import LoginScreen from './components/LoginScreen';
import RegisterScreen from './components/RegisterScreen';
import MessageList from './components/MessageList';
import UnlockForm from './components/UnlockForm';

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

// --- Private Message Client Component (UPDATED) ---
const PrivateMessageClient = ({ setNeedsUnlock, initialRecipient = null }) => {
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showCompose, setShowCompose] = useState(!!initialRecipient);
  
  const [recipientIdentifier, setRecipientIdentifier] = useState(initialRecipient ? initialRecipient.displayName : '');
  const [recipientPubkey, setRecipientPubkey] = useState(initialRecipient ? initialRecipient.pubkey : null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchMessages = useCallback(() => {
    setError('');
    apiClient.get('/api/pm/list/')
      .then(response => setMessages(response.data))
      .catch(err => {
        // CORRECTED: This now correctly handles the identity locked error.
        if (err.response && err.response.data.error === 'identity_locked') {
          setNeedsUnlock(true);
        } else {
          console.error("Error fetching PMs:", err);
          setError("Could not fetch private messages.");
        }
      });
  }, [setNeedsUnlock]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!recipientIdentifier || !subject || !body) {
      setError("Recipient, subject, and body are required.");
      return;
    }
    try {
      const payload = {
        recipient_identifier: recipientIdentifier,
        recipient_pubkey: recipientPubkey,
        subject,
        body
      };
      await apiClient.post('/api/pm/send/', payload);
      setSuccess('Message sent successfully!');
      setRecipientIdentifier('');
      setRecipientPubkey(null);
      setSubject('');
      setBody('');
      setShowCompose(false);
      setTimeout(fetchMessages, 1000);
    } catch (err) {
      if (err.response && err.response.data.error === 'identity_locked') {
        setNeedsUnlock(true);
      } else {
        setError(err.response?.data?.error || 'Failed to send message.');
      }
    }
  };

  if (selectedMessage) {
    return (
      <div>
        <button onClick={() => setSelectedMessage(null)} className="mb-4 bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
          ← Back to Inbox
        </button>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <h3 className="text-xl font-bold text-white mb-1">{selectedMessage.subject}</h3>
          <p className="text-sm text-gray-400 mb-2">From: {selectedMessage.author_username} on {new Date(selectedMessage.created_at).toLocaleString()}</p>
          <p className="text-gray-300 whitespace-pre-wrap mb-4">{selectedMessage.decrypted_body}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <Header text="Private Mail" />
        <button onClick={() => { setShowCompose(!showCompose); setRecipientIdentifier(''); setRecipientPubkey(null); }} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          {showCompose ? 'Cancel' : 'Compose'}
        </button>
      </div>

      {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
      {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>}

      {showCompose && (
        <div className="bg-gray-800 p-4 rounded mb-6 border border-gray-700">
          <form onSubmit={handleSendMessage}>
            <input type="text" placeholder="Recipient's Username or Moo-ID" value={recipientIdentifier} onChange={e => setRecipientIdentifier(e.target.value)} required className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
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
              <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">From</th>
              <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">Received</th>
            </tr>
          </thead>
          <tbody>
            {messages.map(msg => (
              <tr key={msg.id} className="border-b border-gray-700 last:border-b-0 hover:bg-gray-700 cursor-pointer" onClick={() => setSelectedMessage(msg)}>
                <td className="p-3 text-gray-200">{msg.subject}</td>
                <td className="p-3 text-gray-400">{msg.author_username}</td>
                <td className="p-3 text-gray-400">{new Date(msg.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {messages.length === 0 && <p className="text-gray-400 text-center p-4">Your inbox is empty.</p>}
      </div>
    </div>
  );
};


function App() {
  // ... (rest of the App component is unchanged)
}

export default App;
