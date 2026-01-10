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


// Full path: axon_bbs/frontend/src/components/ContactModeratorsModal.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

const ContactModeratorsModal = ({ show, onClose }) => {
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!show) {
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsSubmitting(true);

    if (!comment.trim()) {
        setError('Inquiry cannot be empty.');
        setIsSubmitting(false);
        return;
    }

    try {
      const response = await apiClient.post('/api/moderation/contact/', { comment });
      setSuccess(response.data.status || 'Your inquiry has been sent.');
      setTimeout(() => {
        onClose();
        setComment('');
        setSuccess('');
      }, 2500);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to submit your inquiry.');
    } finally {
        setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-lg">
        <h2 className="text-2xl font-bold text-white mb-4">Contact Moderators</h2>
        
        {success ? (
            <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>
        ) : (
            <form onSubmit={handleSubmit}>
                <p className="text-gray-400 mb-4 text-sm">
                    Use this form for general questions or concerns. To report a specific message, please use the "Report" button on the message itself.
                </p>
                <textarea
                    placeholder="Type your inquiry here..."
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    rows="6"
                    className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"
                />
                {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
                <div className="flex justify-end gap-4">
                    <button type="button" onClick={onClose} disabled={isSubmitting} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50">
                        Cancel
                    </button>
                    <button type="submit" disabled={isSubmitting} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50">
                        {isSubmitting ? 'Sending...' : 'Send Inquiry'}
                    </button>
                </div>
            </form>
        )}
      </div>
    </div>
  );
};

export default ContactModeratorsModal;
