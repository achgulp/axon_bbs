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


// Full path: axon_bbs/frontend/src/components/ReportModal.js
import React, { useState } from 'react';

const ReportModal = ({ message, show, onClose, onSubmit }) => {
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!show) {
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await onSubmit(message.id, comment);
      setSuccess('Report submitted successfully. A moderator will review it shortly.');
      setTimeout(() => {
        onClose();
        setComment('');
        setSuccess('');
      }, 2000); // Close modal after 2 seconds on success
    } catch (err) {
      setError(err.message || 'Failed to submit report.');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-lg">
        <h2 className="text-2xl font-bold text-white mb-4">Report Message</h2>
        <div className="bg-gray-900 p-3 rounded mb-4 border border-gray-700">
            <p className="text-gray-400 text-sm">Subject: <span className="text-gray-200">{message.subject}</span></p>
            <p className="text-gray-400 text-sm">Author: <span className="text-gray-200">{message.author_display}</span></p>
        </div>
        
        {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>}
        
        <form onSubmit={handleSubmit}>
          <textarea
            placeholder="Provide a brief reason for your report (optional)..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows="4"
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"
          />
          {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
          <div className="flex justify-end gap-4">
            <button type="button" onClick={onClose} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">Cancel</button>
            <button type="submit" className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">Submit Report</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReportModal;
