// Full path: axon_bbs/frontend/src/components/MessageList.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';
import UnlockForm from './UnlockForm';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const AttachmentItem = ({ attachment, onDownload }) => {
  const [status, setStatus] = useState('checking');
  // States: 'checking', 'syncing', 'available'

  const fetchStatus = useCallback(() => {
    apiClient.get(`/api/files/status/${attachment.id}/`)
      .then(response => {
        setStatus(response.data.status);
      })
      .catch(err => {
        console.error(`Failed to fetch status for file ${attachment.id}`, err);
        setStatus('error');
      });
  }, [attachment.id]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (status === 'syncing') {
      const interval = setInterval(() => {
        fetchStatus();
      }, 5000); // Check every 5 seconds

      return () => clearInterval(interval);
    }
  }, [status, fetchStatus]);

  return (
    <li key={attachment.id} className="flex items-center gap-4">
      <span className="text-gray-200">{attachment.filename}</span>
      <span className="text-gray-400 text-sm">({Math.round(attachment.size / 1024)} KB)</span>
      <div className="flex-grow"></div> {/* Spacer */}
      {status === 'available' && (
        <button onClick={() => onDownload(attachment.id, attachment.filename)} className="text-blue-400 hover:text-blue-300 hover:underline">
          Download
        </button>
      )}
      {status === 'syncing' && (
        <span className="text-yellow-400 text-sm italic">Syncing in progress...</span>
      )}
      {status === 'checking' && (
        <span className="text-gray-400 text-sm italic">Checking status...</span>
      )}
      {status === 'error' && (
        <span className="text-red-500 text-sm italic">Error</span>
      )}
    </li>
  );
};


const MessageList = ({ board, onBack, onStartPrivateMessage }) => {
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showPostForm, setShowPostForm] = useState(false);
  const [needsUnlock, setNeedsUnlock] = useState(false);
  const [postUnlockAction, setPostUnlockAction] = useState(null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');

  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [attachments, setAttachments] = useState([]);

  const fetchMessages = useCallback(async () => {
    try {
      const response = await apiClient.get(`/api/boards/${board.id}/messages/`);
      setMessages(response.data);
    } catch (err) { console.error("Failed to fetch messages:", err); }
  }, [board.id]);

  useEffect(() => { fetchMessages(); }, [fetchMessages]);

  const handlePostMessage = useCallback(async () => {
    setError('');
    if (!subject || !body) { setError("Subject and body cannot be empty."); return; }
    try {
      const attachment_ids = attachments.map(att => att.id);
      await apiClient.post('/api/messages/post/', { subject, body, board_name: board.name, attachment_ids });
      setSubject(''); setBody(''); setAttachments([]); setShowPostForm(false);
      fetchMessages();
    } catch (err) {
      if (err.response && err.response.data.error === 'identity_locked') {
        setPostUnlockAction(() => () => handlePostMessage());
        setNeedsUnlock(true);
      } else {
        setError(err.response?.data?.error || 'Could not post message.');
      }
    }
  }, [subject, body, board.name, attachments, fetchMessages]);

  const handleFileUpload = async () => {
    if (!selectedFile) { setUploadError('Please select a file first.'); return; }
    setIsUploading(true); setUploadError('');
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await apiClient.post('/api/files/upload/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setAttachments(prev => [...prev, response.data]);
      setSelectedFile(null);
    } catch (err) {
      setUploadError(err.response?.data?.error || 'File upload failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileDownload = useCallback(async (fileId, filename) => {
    try {
      const response = await apiClient.get(`/api/files/download/${fileId}/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err.response && err.response.status === 401) {
        setPostUnlockAction(() => () => handleFileDownload(fileId, filename));
        setNeedsUnlock(true);
      } else {
        console.error("Download failed:", err);
        alert("Could not download the file. See console for details.");
      }
    }
  }, []);
  
  // NEW: Handle public reply
  const handleReply = () => {
    if (!selectedMessage) return;
    const quotedBody = selectedMessage.body.split('\n').map(line => `> ${line}`).join('\n');
    setSubject(`Re: ${selectedMessage.subject}`);
    setBody(`\n\nOn ${new Date(selectedMessage.created_at).toLocaleString()}, ${selectedMessage.author_display} wrote:\n${quotedBody}`);
    setSelectedMessage(null); // Go back to message list view
    setShowPostForm(true); // Show the pre-filled form
  };

  const handleUnlockSuccess = () => {
    setNeedsUnlock(false);
    if (postUnlockAction) {
      postUnlockAction();
      setPostUnlockAction(null);
    }
  };

  if (selectedMessage) {
    return (
      <div>
        <div className="flex justify-between items-center mb-4">
            <button onClick={() => setSelectedMessage(null)} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
              ← Back to {board.name}
            </button>
            {/* NEW: Reply and PM Buttons */}
            <div className="flex gap-2">
                <button onClick={handleReply} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                    Reply
                </button>
                <button onClick={() => onStartPrivateMessage(selectedMessage.pubkey, selectedMessage.author_display)} className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded">
                    Send Private Message
                </button>
            </div>
        </div>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <h3 className="text-xl font-bold text-white mb-1">{selectedMessage.subject}</h3>
          <p className="text-sm text-gray-400 mb-2">by {selectedMessage.author_display} on {new Date(selectedMessage.created_at).toLocaleString()}</p>
          <p className="text-gray-300 whitespace-pre-wrap mb-4">{selectedMessage.body}</p>
          
          {selectedMessage.attachments && selectedMessage.attachments.length > 0 && (
            <div className="border-t border-gray-700 pt-4 mt-4">
              <h4 className="font-bold text-gray-300 mb-2">Attachments:</h4>
              <ul className="space-y-2">
                {selectedMessage.attachments.map(att => (
                  <AttachmentItem key={att.id} attachment={att} onDownload={handleFileDownload} />
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      {needsUnlock && <UnlockForm onUnlock={handleUnlockSuccess} onCancel={() => { setNeedsUnlock(false); setPostUnlockAction(null); }} />}
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
            <input type="text" placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} required className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <textarea placeholder="Your message..." value={body} onChange={(e) => setBody(e.target.value)} required rows="5" className="w-full py-2 px-3 bg-gray-700 text-gray-200 rounded mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <div className="bg-gray-700 p-3 rounded mb-4">
              <label className="block text-gray-300 text-sm font-bold mb-2">Attach Files</label>
              <div className="flex items-center gap-4">
                <input type="file" onChange={(e) => setSelectedFile(e.target.files[0])} className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"/>
                <button type="button" onClick={handleFileUpload} disabled={isUploading || !selectedFile} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-500">
                  {isUploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
              {uploadError && <p className="text-red-500 text-xs italic mt-2">{uploadError}</p>}
              {attachments.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-bold text-gray-300">Attached:</h4>
                  <ul className="list-disc list-inside text-gray-400">
                    {attachments.map((att) => (
                      <li key={att.id}>
                        {att.filename}
                        <button type="button" onClick={() => setAttachments(prev => prev.filter(a => a.id !== att.id))} className="ml-2 text-red-500 hover:text-red-400">[remove]</button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
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
              <tr key={msg.id} className="border-b border-gray-700 last:border-b-0 hover:bg-gray-700 cursor-pointer" onClick={() => setSelectedMessage(msg)}>
                <td className="p-3 text-gray-200">
                  {msg.subject}
                  {msg.attachments && msg.attachments.length > 0 && <span className="ml-2 text-xs text-blue-400">[+{msg.attachments.length} file(s)]</span>}
                </td>
                <td className="p-3 text-gray-400">{msg.author_display}</td>
                <td className="p-3 text-gray-400">{new Date(msg.created_at).toLocaleString()}</td>
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
