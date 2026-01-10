// Axon BBS - A modern, anonymous, federated bulletin board system.
// Copyright (C) 2025 Achduke7
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.


// Full path: axon_bbs/frontend/src/components/PrivateMessageClient.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';
// DELETED: The UnlockForm import is removed.

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

// MODIFIED: The component now accepts the onIdentityLocked prop.
const PrivateMessageClient = ({ initialRecipient = null, displayTimezone, onIdentityLocked }) => {
  const [view, setView] = useState('inbox');
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [recipientIdentifier, setRecipientIdentifier] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');

  // DELETED: State for manual unlock is no longer needed.

  const fetchMessages = useCallback(async () => {
    setIsLoading(true);
    setError('');
    const endpoint = view === 'inbox' ? '/api/pm/list/' : '/api/pm/outbox/';
    try {
      const response = await apiClient.get(endpoint);
      setMessages(response.data);
    } catch (err) {
      if (err.response?.data?.error === 'identity_locked') {
        // MODIFIED: Call the logout handler from App.js
        onIdentityLocked();
      } else {
        setError('Could not fetch messages.');
        console.error(`Error fetching ${view}:`, err);
      }
    } finally {
      setIsLoading(false);
    }
  }, [view, onIdentityLocked]);

  useEffect(() => {
    if (view === 'inbox' || view === 'outbox') {
      fetchMessages();
    }
  }, [view, fetchMessages]);

  useEffect(() => {
    if (initialRecipient) {
        setRecipientIdentifier(initialRecipient.displayName);
        setView('compose');
    }
  }, [initialRecipient]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
        await apiClient.post('/api/pm/send/', { recipient_identifier: recipientIdentifier, subject, body });
        setRecipientIdentifier(''); 
        setSubject(''); 
        setBody('');
        setView('outbox');
    } catch(err) {
        if (err.response?.data?.error === 'identity_locked') {
            onIdentityLocked();
          } else {
            setError(err.response?.data?.error || 'Could not send message.');
        }
    } finally {
        setIsLoading(false);
    }
  };

  const handleReply = () => {
    const original = selectedMessage;
    setSelectedMessage(null);
    setView('compose');
    setRecipientIdentifier(original.author_display);
    setSubject(`Re: ${original.decrypted_subject}`);
    const quoteHeader = `\n\nOn ${new Date(original.created_at).toLocaleString([], { timeZone: displayTimezone })}, ${original.author_display} wrote:\n`;
    const quotedBody = (original.decrypted_body || '').split('\n').map(line => `> ${line}`).join('\n');
    setBody(quoteHeader + quotedBody + '\n');
  };

  const handleForward = () => {
    const original = selectedMessage;
    setSelectedMessage(null);
    setView('compose');
    setRecipientIdentifier('');
    setSubject(`Fwd: ${original.decrypted_subject}`);
    const forwardedBody = (original.decrypted_body || '').split('\n').map(line => `> ${line}`).join('\n');
    setBody(`\n\n--- Forwarded Message ---\nFrom: ${original.author_display}\nDate: ${new Date(original.created_at).toLocaleString([], { timeZone: displayTimezone })}\nSubject: ${original.decrypted_subject}\n\n${forwardedBody}`);
  };

  const handleDelete = async (messageId) => {
    if (!window.confirm("Are you sure you want to permanently delete this message?")) {
      return;
    }
    setError('');
    try {
      await apiClient.delete(`/api/pm/delete/${messageId}/`);
      setSelectedMessage(null);
      fetchMessages();
    } catch (err) {
      setError(err.response?.data?.error || 'Could not delete the message.');
      console.error('Error deleting PM:', err);
    }
  };

  const renderMessageList = () => (
    <div className="bg-gray-800 rounded border border-gray-700">
      <table className="w-full text-left table-auto">
        <thead className="border-b border-gray-600">
          <tr>
            <th className="p-3 text-sm font-semibold text-gray-400 w-2/5">Subject</th>
            <th className="p-3 text-sm font-semibold text-gray-400 w-2/5">{view === 'inbox' ? 'From' : 'To'}</th>
            <th className="p-3 text-sm font-semibold text-gray-400 w-1/5">Date</th>
            <th className="p-3 text-sm font-semibold text-gray-400 text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {messages.map(msg => (
            <tr key={msg.id} className="border-b border-gray-700 last:border-b-0 hover:bg-gray-700">
              <td className="p-3 text-gray-200 cursor-pointer" onClick={() => { setView(view); setSelectedMessage(msg); }}>{msg.decrypted_subject || msg.subject}</td>
              <td className="p-3 text-gray-400 flex items-center gap-2 cursor-pointer" onClick={() => { setView(view); setSelectedMessage(msg); }}>
                <img src={(msg.author_avatar_url || msg.recipient_avatar_url) || '/default_avatar.png'} alt="avatar" className="w-8 h-8 rounded-full bg-gray-700" />
                {msg.author_display || msg.recipient_display}
              </td>
              <td className="p-3 text-gray-400 cursor-pointer" onClick={() => { setView(view); setSelectedMessage(msg); }}>{new Date(msg.created_at).toLocaleString([], { timeZone: displayTimezone })}</td>
              <td className="p-3 text-center">
                <button 
                  onClick={(e) => { e.stopPropagation(); handleDelete(msg.id); }} 
                  className="text-red-500 hover:text-red-400 text-sm font-semibold"
                  title="Delete Message"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {messages.length === 0 && <p className="text-gray-400 text-center p-4">Your {view} is empty.</p>}
    </div>
  );

  const renderReadMessage = () => {
    const msg = selectedMessage;
    const isInboxMessage = !!msg.author_display;
    return (
     <div>
            <div className="flex justify-between items-center mb-4">
                <button onClick={() => setSelectedMessage(null)} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
                ← Back to {view}
                </button>
                <div className="flex gap-2">
                    {isInboxMessage && <button onClick={handleReply} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Reply</button>}
                    <button onClick={handleForward} className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded">Forward</button>
                    <button onClick={() => handleDelete(msg.id)} className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">Delete</button>
                </div>
            </div>
            <div className="bg-gray-800 p-4 rounded border border-gray-700">
                <h3 className="text-xl font-bold text-white mb-1">{msg.decrypted_subject}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                    <img src={(msg.author_avatar_url || msg.recipient_avatar_url) || '/default_avatar.png'} alt="avatar" className="w-6 h-6 rounded-full bg-gray-700" />
                    <span>{isInboxMessage ? `From: ${msg.author_display}` : `To: ${msg.recipient_display}`} on {new Date(msg.created_at).toLocaleString([], { timeZone: displayTimezone })}</span>
                </div>
                <p className="text-gray-300 whitespace-pre-wrap p-2 border-t border-gray-700 mt-2">{msg.decrypted_body || 'Message content is encrypted and could not be displayed.'}</p>
            </div>
        </div>
    );
  };

  const renderCompose = () => (
    <div>
        <Header text="Compose Private Message" />
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <form onSubmit={handleSendMessage}>
                <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-bold mb-2">Recipient</label>
                    <input type="text" placeholder="Enter username, nickname, or alias" value={recipientIdentifier} onChange={e => setRecipientIdentifier(e.target.value)} required className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <input type="text" placeholder="Subject" value={subject} onChange={e => setSubject(e.target.value)} required className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <textarea placeholder="Your message..." value={body} onChange={e => setBody(e.target.value)} required rows="8" className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
                <div className="flex justify-end gap-4">
                    <button type="button" onClick={() => { setView('inbox'); setSelectedMessage(null); }} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">Cancel</button>
                    <button type="submit" disabled={isLoading} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-500">{isLoading ? 'Sending...' : 'Send Message'}</button>
                </div>
            </form>
        </div>
    </div>
  );
  
  const renderContent = () => {
    if (selectedMessage) return renderReadMessage();
    if (view === 'compose') return renderCompose();
    return renderMessageList();
  };
  
  return (
    <div>
        {/* DELETED: The UnlockForm has been removed */}
        {!selectedMessage && view !== 'compose' && (
            <div className="flex justify-between items-center mb-4">
                <Header text={view === 'inbox' ? 'Private Mail - Inbox' : 'Private Mail - Outbox'} />
                <div>
                    <button onClick={() => setView(view === 'inbox' ? 'outbox' : 'inbox')} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded mr-2">
                        View {view === 'inbox' ? 'Outbox' : 'Inbox'}
                    </button>
                    <button onClick={() => { setView('compose'); setSubject(''); setBody(''); setRecipientIdentifier(''); }} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                        New Message
                    </button>
                </div>
            </div>
        )}
        {isLoading ? <div>Loading messages...</div> : error ? <p className="text-red-500">{error}</p> : renderContent()}
    </div>
  );
};

export default PrivateMessageClient;
