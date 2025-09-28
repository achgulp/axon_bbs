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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.


// Full path: axon_bbs/frontend/src/components/MessageList.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';
import ReportModal from './ReportModal';
import AppletRunner from './AppletRunner';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const AttachmentItem = ({ attachment, handlerApplet, onLaunch }) => {
  if (handlerApplet) {
    return (
        <li className="flex items-center gap-4">
            <span className="text-gray-200">{attachment.filename}</span>
            <span className="text-gray-400 text-sm">({Math.round(attachment.size / 1024)} KB)</span>
            <div className="flex-grow"></div>
            <button onClick={() => onLaunch(handlerApplet, attachment)} className="text-blue-400 hover:text-blue-300 hover:underline">
                View Embedded
            </button>
        </li>
    );
  }

  return (
    <li className="flex items-center gap-4">
      <span className="text-gray-200">{attachment.filename}</span>
      <span className="text-gray-400 text-sm">({Math.round(attachment.size / 1024)} KB)</span>
       <div className="flex-grow"></div>
       <span className="text-gray-500 text-sm italic">No viewer available</span>
    </li>
  );
};


const MessageList = ({ board, onBack, onStartPrivateMessage, displayTimezone, onIdentityLocked }) => {
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showPostForm, setShowPostForm] = useState(false);
  // DELETED: State for manual unlock is no longer needed
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [showReportModal, setShowReportModal] = useState(false);
  const [applets, setApplets] = useState([]);
  const [viewingApplet, setViewingApplet] = useState(null);

  const fetchMessages = useCallback(async () => {
    try {
      const [msgResponse, appletResponse] = await Promise.all([
          apiClient.get(`/api/boards/${board.id}/messages/`),
          apiClient.get('/api/applets/')
      ]);
      setMessages(msgResponse.data);
      setApplets(appletResponse.data);
    } catch (err) { console.error("Failed to fetch messages or applets:", err); }
  }, [board.id]);
  
  useEffect(() => { fetchMessages(); }, [fetchMessages]);

  const findHandlerAppletFor = (mimeType) => {
      if (!mimeType) return null;
      return applets.find(applet => 
          applet.handles_mime_types && applet.handles_mime_types.split(',').map(m => m.trim()).includes(mimeType)
      );
  };
  
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
        // MODIFIED: Call the logout handler from App.js
        onIdentityLocked();
      } else {
        setError(err.response?.data?.error || 'Could not post message.');
      }
    }
  }, [subject, body, board.name, attachments, fetchMessages, onIdentityLocked]);

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
      if (err.response?.data?.error === 'identity_locked') {
          onIdentityLocked();
      } else {
          setUploadError(err.response?.data?.error || 'File upload failed.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleReply = () => {
    if (!selectedMessage) return;
    const quotedBody = selectedMessage.body.split('\n').map(line => `> ${line}`).join('\n');
    setSubject(`Re: ${selectedMessage.subject}`);
    setBody(`\n\nOn ${new Date(selectedMessage.created_at).toLocaleString([], { timeZone: displayTimezone })}, ${selectedMessage.author_display} wrote:\n${quotedBody}`);
    setSelectedMessage(null);
    setShowPostForm(true);
  };
  
  // DELETED: handleUnlockSuccess is no longer needed

  const handleReportSubmit = async (message_id, comment) => {
    try {
        await apiClient.post('/api/messages/report/', { message_id, comment });
    } catch (err) {
        console.error("Failed to submit report:", err);
        throw new Error(err.response?.data?.error || 'An unexpected error occurred.');
    }
  };

  if (viewingApplet) {
      return (
          <div className="fixed inset-0 bg-black bg-opacity-90 z-50 flex flex-col p-4">
              <AppletRunner 
                  key={viewingApplet.attachment.id}
                  applet={viewingApplet.applet}
                  attachmentContext={{
                      content_hash: viewingApplet.attachment.metadata_manifest.content_hash,
                      content_type: viewingApplet.attachment.content_type,
                      filename: viewingApplet.attachment.filename,
                  }}
                  onBack={() => setViewingApplet(null)}
              />
          </div>
      );
  }
  
  if (selectedMessage) {
    return (
      <div>
        <ReportModal 
            message={selectedMessage}
            show={showReportModal} 
            onClose={() => setShowReportModal(false)}
            onSubmit={handleReportSubmit}
        />
        <div className="flex justify-between items-center mb-4">
             <button onClick={() => setSelectedMessage(null)} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
              ← Back to {board.name}
             </button>
             <div className="flex gap-2">
                <button onClick={handleReply} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                   Reply
                </button>
                <button onClick={() => onStartPrivateMessage(selectedMessage.pubkey, selectedMessage.author_display)} className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded">
                    Send Private Message
                </button>
                <button onClick={() => setShowReportModal(true)} className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
                    Report
                </button>
            </div>
        </div>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <h3 className="text-xl font-bold text-white mb-1">{selectedMessage.subject}</h3>
           <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
            <img src={selectedMessage.author_avatar_url || '/default_avatar.png'} alt="author avatar" className="w-6 h-6 rounded-full bg-gray-700" />
            <span>by {selectedMessage.author_display} on {new Date(selectedMessage.created_at).toLocaleString([], { timeZone: displayTimezone })}</span>
          </div>
          <p className="text-gray-300 whitespace-pre-wrap mb-4">{selectedMessage.body}</p>
          
          {selectedMessage.attachments && selectedMessage.attachments.length > 0 && (
            <div className="border-t border-gray-700 pt-4 mt-4">
              <h4 className="font-bold text-gray-300 mb-2">Attachments:</h4>
              <ul className="space-y-2">
                {selectedMessage.attachments.map(att => (
                  <AttachmentItem 
                    key={att.id} 
                    attachment={att} 
                    handlerApplet={findHandlerAppletFor(att.content_type)}
                    onLaunch={(applet, attachment) => setViewingApplet({applet, attachment})}
                  />
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
      {/* DELETED: The UnlockForm has been removed */}
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
                <td className="p-3 text-gray-400 flex items-center gap-2">
                  <img src={msg.author_avatar_url || '/default_avatar.png'} alt="author avatar" className="w-8 h-8 rounded-full bg-gray-700" />
                  {msg.author_display}
                </td>
                <td className="p-3 text-gray-400">{new Date(msg.created_at).toLocaleString([], { timeZone: displayTimezone })}</td>
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
