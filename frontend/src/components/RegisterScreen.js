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


// Full path: axon_bbs/frontend/src/components/RegisterScreen.js
import React, { useState } from 'react';
import apiClient from '../apiClient';
const RegisterScreen = ({ onRegisterSuccess, onNavigateToLogin }) => {
  const [username, setUsername] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [question1, setQuestion1] = useState('');
  const [answer1, setAnswer1] = useState('');
  const [question2, setQuestion2] = useState('');
  const [answer2, setAnswer2] = useState('');
  const [error, setError] = useState('');

  const [view, setView] = useState('register'); // 'register' or 'claim'
  const [keyFile, setKeyFile] = useState(null);
  const [claimPassword, setClaimPassword] = useState('');
  const [keyFilePassword, setKeyFilePassword] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== password2) {
      setError("Passwords do not match.");
      return;
    }

    try {
      await apiClient.post('/api/register/', {
        username,
        password,
        nickname,
        security_question_1: question1,
        security_answer_1: answer1,
        security_question_2: question2,
        security_answer_2: answer2,
      });
      onRegisterSuccess();
    } catch (err) {
      if (err.response && err.response.status === 409 && err.response.data.error.endsWith('_exists_as_federated')) {
        setError(err.response.data.detail);
        setView('claim');
      } else if (err.response && err.response.data) {
        const errorData = err.response.data;
        const messages = Object.values(errorData).flat();
        setError(messages.join(' ') || 'An unexpected error occurred during registration.');
      } else {
        setError('An unexpected error occurred during registration.');
      }
      console.error(err);
    }
  };

  const handleClaim = async (e) => {
    e.preventDefault();
    setError('');
    if (!keyFile) {
        setError('Please select your private key file to continue.');
        return;
    }
    const formData = new FormData();
    // --- MODIFICATION START ---
    formData.append('username', username); // Send the desired username
    formData.append('nickname', nickname);
    // --- MODIFICATION END ---
    formData.append('new_password', claimPassword);
    formData.append('key_file', keyFile);
    if (keyFilePassword) {
        formData.append('key_file_password', keyFilePassword);
    }

    try {
        const response = await apiClient.post('/api/identity/claim/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        localStorage.setItem('token', response.data.access);
        onRegisterSuccess();
    } catch (err) {
        setError(err.response?.data?.error || 'Failed to claim account. Please check your key file and password.');
    }
  };

  if (view === 'claim') {
    return (
        <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
            <div className="flex items-center text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">
                <img src="/axon.png" alt="Axon logo" className="h-24 w-24 mr-4"/>
                <h1>Claim Identity</h1>
            </div>
            <p className="text-yellow-300 bg-yellow-900 border border-yellow-700 p-3 rounded mb-4 text-sm">{error}</p>
            <form onSubmit={handleClaim}>
                <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-bold mb-2">Nickname to Claim</label>
                    <input type="text" value={nickname} readOnly className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-900 text-gray-400 leading-tight focus:outline-none"/>
                </div>
                <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-bold mb-2">Your Private Key File (.pem)</label>
                    <input type="file" onChange={e => setKeyFile(e.target.files[0])} accept=".pem" required className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"/>
                </div>
                <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-bold mb-2">Password for Key File (if encrypted)</label>
                    <input type="password" value={keyFilePassword} onChange={e => setKeyFilePassword(e.target.value)} placeholder="Leave blank if not encrypted" className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
                </div>
                <div className="mb-6">
                    <label className="block text-gray-300 text-sm font-bold mb-2">New Password for this BBS</label>
                    <input type="password" value={claimPassword} onChange={e => setClaimPassword(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
                </div>
                <div className="flex flex-col items-center justify-between">
                    <button type="submit" className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded w-full">Verify Key & Claim Account</button>
                    <button onClick={onNavigateToLogin} className="inline-block align-baseline font-bold text-sm text-blue-400 hover:text-blue-500 mt-4" type="button">Back to Login</button>
                </div>
            </form>
        </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
      <div className="flex items-center text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">
        <img src="/axon.png" alt="Axon logo" className="h-24 w-24 mr-4"/>
        <h1>Register</h1>
      </div>
      <form onSubmit={handleRegister}>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="username">Username</label>
          <input className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200" id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="nickname">Nickname</label>
          <input className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200" id="nickname" type="text" value={nickname} onChange={(e) => setNickname(e.target.value)} required />
        </div>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password">Password</label>
          <input className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200" id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div className="mb-6">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password2">Confirm Password</label>
          <input className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200" id="password2" type="password" value={password2} onChange={(e) => setPassword2(e.target.value)} required />
        </div>

        <div className="border-t border-gray-700 pt-4 mt-4">
            <p className="text-gray-400 text-sm mb-4">Set up two security questions for account recovery. Answers are case-sensitive.</p>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="question1">Security Question 1</label>
                <input id="question1" type="text" placeholder="e.g., What was your first pet's name?" value={question1} onChange={e => setQuestion1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200"/>
            </div>
            <div className="mb-6">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="answer1">Security Answer 1</label>
                <input id="answer1" type="password" value={answer1} onChange={e => setAnswer1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200"/>
            </div>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="question2">Security Question 2</label>
                <input id="question2" type="text" placeholder="e.g., What city were you born in?" value={question2} onChange={e => setQuestion2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200"/>
            </div>
            <div className="mb-6">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="answer2">Security Answer 2</label>
                <input id="answer2" type="password" value={answer2} onChange={e => setAnswer2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200"/>
            </div>
        </div>

        {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
        <div className="flex flex-col items-center justify-between">
          <button className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded w-full" type="submit">Register</button>
          <button onClick={onNavigateToLogin} className="inline-block align-baseline font-bold text-sm text-blue-400 hover:text-blue-500 mt-4" type="button">Already have an account? Login</button>
        </div>
      </form>
    </div>
  );
};

export default RegisterScreen;
