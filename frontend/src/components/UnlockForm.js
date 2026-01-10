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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.


// Full path: axon_bbs/frontend/src/components/UnlockForm.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

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
        <p className="text-gray-400 mb-4">Enter your password to sign messages and download files for this session.</p>
        <form onSubmit={handleUnlock}>
          <input type="password" placeholder="Your Password" value={password} onChange={(e) => setPassword(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline mb-4"/>
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

export default UnlockForm;

