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


// Full path: axon_bbs/frontend/src/components/RegisterScreen.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

const RegisterScreen = ({ onRegisterSuccess, onNavigateToLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  // --- NEW: State for security questions ---
  const [question1, setQuestion1] = useState('');
  const [answer1, setAnswer1] = useState('');
  const [question2, setQuestion2] = useState('');
  const [answer2, setAnswer2] = useState('');
  const [error, setError] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== password2) {
      setError("Passwords do not match.");
      return;
    }

    try {
      // --- MODIFIED: Send all required fields ---
      await apiClient.post('/api/register/', {
        username,
        password,
        security_question_1: question1,
        security_answer_1: answer1,
        security_question_2: question2,
        security_answer_2: answer2,
      });
      onRegisterSuccess();
    } catch (err) {
      if (err.response && err.response.data) {
        // Attempt to format a more helpful error message
        const errorData = err.response.data;
        const messages = Object.values(errorData).flat();
        setError(messages.join(' ') || 'An unexpected error occurred during registration.');
      } else {
        setError('An unexpected error occurred during registration.');
      }
      console.error(err);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
      <div className="flex items-center text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">
        <img src="/axon.png" alt="Axon logo" className="h-24 w-24 mr-4"/>
        <h1>Register</h1>
      </div>
      <form onSubmit={handleRegister}>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="username">
            Username
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"
            id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required
          />
        </div>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password">
            Password
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"
            id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
          />
        </div>
        <div className="mb-6">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password2">
            Confirm Password
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            id="password2" type="password" value={password2} onChange={(e) => setPassword2(e.target.value)} required
          />
        </div>

        {/* --- NEW: Security Question Fields --- */}
        <div className="border-t border-gray-700 pt-4 mt-4">
            <p className="text-gray-400 text-sm mb-4">Set up two security questions for account recovery. Answers are case-sensitive.</p>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="question1">Security Question 1</label>
                <input id="question1" type="text" placeholder="e.g., What was your first pet's name?" value={question1} onChange={e => setQuestion1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
            <div className="mb-6">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="answer1">Security Answer 1</label>
                <input id="answer1" type="password" value={answer1} onChange={e => setAnswer1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="question2">Security Question 2</label>
                <input id="question2" type="text" placeholder="e.g., What city were you born in?" value={question2} onChange={e => setQuestion2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
            <div className="mb-6">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="answer2">Security Answer 2</label>
                <input id="answer2" type="password" value={answer2} onChange={e => setAnswer2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
        </div>
        {/* --- END: Security Question Fields --- */}

        {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
        <div className="flex flex-col items-center justify-between">
          <button
            className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full"
            type="submit"
          >
            Register
          </button>
          <button
            onClick={onNavigateToLogin}
            className="inline-block align-baseline font-bold text-sm text-blue-400 hover:text-blue-500 mt-4"
            type="button"
          >
            Already have an account? Login
          </button>
        </div>
      </form>
    </div>
  );
};

export default RegisterScreen;
