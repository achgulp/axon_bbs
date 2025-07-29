// Full path: axon_bbs/frontend/src/components/MessageList.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';
const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

const UnlockForm = ({ onUnlock, onCancel }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  
  const handleUnlock = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await apiClient.post('/api/identity/unlock/', { password });
      onUnlock();
    } catch (err) {
      setError('Unlock failed. Please check your password.');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-sm">
        <h2 className="text-2xl font-bold text-white mb-4">Unlock Identity</h2>
        <p className="text-gray-400 mb-4">Enter your password to sign messages for this session.</p>
        <form onSubmit={handleUnlock}>
          <input
            type="password"
            placeholder="Your Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"
          />
          {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
          <div className="flex justify-end gap-4">
            <button type="button" onClick={onCancel} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">Cancel</button>
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Unlock</button>
          </div>
        </form>
      </div>
    </div>
  );
};

const MessageList = ({ board, onBack }) => {
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showPostForm, setShowPostForm] = useState(false);
  const [needsUnlock, setNeedsUnlock] = useState(false);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');

  const fetchMessages = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/boards/${board.id}/messages/`);
      const msgs = response.data.map(msg => ({
        id: msg.id,
        subject: msg.subject,
        body: msg.body,
        author_display: msg.author_display,
        // CORRECTED: Ensure the date string is correctly parsed by the browser.
        // new Date() can handle ISO 8601 strings directly.
        postedAt: new Date(msg.created_at).toLocaleString(),
      }));
      setMessages(msgs);
    } catch (err) {
      console.error("Failed to fetch messages:", err);
    }
  }, [board.id]);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const handlePostMessage = useCallback(async () => {
    setError('');
    if (!subject || !body) {
      setError("Subject and body cannot be empty.");
      return;
    }
    try {
      await apiClient.post('/api/messages/post/', { subject, body, board_name: board.name });
      setSubject(''); setBody(''); setShowPostForm(false);
      fetchMessages();
    } catch (err) {
      if (err.response && err.response.data.error === 'identity_locked') {
        setNeedsUnlock(true);
      } else {
        setError(err.response?.data?.error || 'Could not post message.');
      }
    }
  }, [subject, body, board.name, fetchMessages]);

  const handleUnlockSuccess = () => {
    setNeedsUnlock(false);
    handlePostMessage();
  };

  if (selectedMessage) {
    return (
      <div>
        <button onClick={() => setSelectedMessage(null)} className="mb-4 bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
          ← Back to {board.name}
        </button>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <h3 className="text-xl font-bold text-white mb-1">{selectedMessage.subject}</h3>
          <p className="text-sm text-gray-400 mb-2">by {selectedMessage.author_display} on {selectedMessage.postedAt}</p>
          <p className="text-gray-300 whitespace-pre-wrap">{selectedMessage.body}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {needsUnlock && <UnlockForm onUnlock={handleUnlockSuccess} onCancel={() => setNeedsUnlock(false)} />}
      
      <div className="flex justify-between items-center mb-4">
        <Header text={board.name} />
        <div>
          <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded mr-2">← Boards</button>
          <button onClick={() => setShowPostForm(!showPostForm)} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            {showPostForm ? 'Cancel' : 'New Post'}
          </button>
        </div>
      </div>

      {showPostForm && (
        <div className="bg-gray-800 p-4 rounded mb-6 border border-gray-700">
          <form onSubmit={(e) => { e.preventDefault(); handlePostMessage(); }}>
            <input
              type="text"
              placeholder="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <textarea
              placeholder="Your message..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows="5"
              className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
            <div className="text-right">
              <button type="submit" className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Submit Post</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-gray-800 rounded border border-gray-700">
        <table className="w-full text-left table-auto">
          <thead className="border-b border-gray-600">
            <tr>
              <th className="p-3 text-sm font-semibold text-gray-400 w-3/5">Thread / Subject</th>
              <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">Author</th>
              <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">Last Post</th>
            </tr>
          </thead>
          <tbody>
            {messages.map(msg => (
              <tr
                key={msg.id}
                className="border-b border-gray-700 last:border-b-0 hover:bg-gray-700 cursor-pointer"
                onClick={() => setSelectedMessage(msg)}
              >
                <td className="p-3 text-gray-200">{msg.subject}</td>
                <td className="p-3 text-gray-400">{msg.author_display}</td>
                <td className="p-3 text-gray-400">{msg.postedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {messages.length === 0 && <p className="text-gray-400 text-center p-4">No messages yet on this board...</p>}
      </div>
    </div>
  );
};

export default MessageList;

