// axon_bbs/frontend/src/components/MessageList.js
import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../apiClient';

const MessageList = ({ boardId, boardName }) => {
  const [messages, setMessages] = useState([]);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPostForm, setShowPostForm] = useState(false);
  const nostrSocket = useRef(null);

  useEffect(() => {
    const relayUrl = 'wss://relay.damus.io';
    nostrSocket.current = new WebSocket(relayUrl);

    nostrSocket.current.onopen = () => {
      console.log(`Connected to Nostr relay: {relayUrl}`);
      const subId = `sub-board-${boardId}-${Date.now()}`;
      const filters = {
        kinds: [1],
        '#t': [boardName],
        limit: 20,
      };
      const request = ["REQ", subId, filters];
      nostrSocket.current.send(JSON.stringify(request));
    };

    nostrSocket.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data[0] === 'EVENT') {
        const nostrEvent = data[2];
        setMessages(prev => {
            if (prev.some(msg => msg.id === nostrEvent.id)) {
                return prev;
            }
            return [nostrEvent, ...prev].sort((a, b) => b.created_at - a.created_at);
        });
      }
    };

    nostrSocket.current.onerror = (err) => {
      console.error("Nostr WebSocket error:", err);
    };

    return () => {
      if (nostrSocket.current) {
        nostrSocket.current.close();
      }
    };
  }, [boardId, boardName]);

  const handlePostMessage = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await apiClient.post('/api/messages/post/', {
        subject,
        body,
        password,
        board_name: boardName
      });
      setSubject('');
      setBody('');
      setPassword('');
      setShowPostForm(false);
    } catch (err) {
      setError('Could not post message. Check password and try again.');
      console.error(err);
    }
  };

  return (
    <div>
      {!showPostForm && (
        <button
          onClick={() => setShowPostForm(true)}
          className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded w-full mb-4"
        >
          Post New Message
        </button>
      )}

      {showPostForm && (
        <div className="bg-gray-800 p-4 rounded mb-6">
          <form onSubmit={handlePostMessage}>
            <input
              type="text"
              placeholder="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"
            />
            <textarea
              placeholder="Your message..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows="4"
              className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"
            />
            <input
              type="password"
              placeholder="Enter your password to sign"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"
            />
            {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
            <div className="flex justify-end gap-4">
              <button
                type="button"
                onClick={() => setShowPostForm(false)}
                className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
              >
                Submit
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-4">
        {messages.length === 0 && (
            <p className="text-gray-400 text-center">Listening for messages on this board...</p>
        )}
        {messages.map(msg => {
          const contentParts = msg.content.split('\n\n');
          const subject = contentParts.length > 1 ? contentParts[0].replace('Subject: ', '') : 'No Subject';
          const body = contentParts.length > 1 ? contentParts.slice(1).join('\n\n') : msg.content;

          return (
            <div key={msg.id} className="bg-gray-800 p-4 rounded">
              <h3 className="text-xl font-bold text-white mb-1">{subject}</h3>
              <p className="text-sm text-gray-400 mb-2">by {msg.pubkey.substring(0, 8)}... on {new Date(msg.created_at * 1000).toLocaleString()}</p>
              <p className="text-gray-300 whitespace-pre-wrap">{body}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MessageList;
