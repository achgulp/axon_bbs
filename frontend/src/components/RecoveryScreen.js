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


// Full path: axon_bbs/frontend/src/components/RecoveryScreen.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

const RecoveryScreen = ({ onNavigateToLogin }) => {
  const [step, setStep] = useState(1); // 1: enter username, 2: answer questions
  const [username, setUsername] = useState('');
  const [questions, setQuestions] = useState(null);
  const [answer1, setAnswer1] = useState('');
  const [answer2, setAnswer2] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await apiClient.post('/api/recovery/get_questions/', { username });
      setQuestions(response.data);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not find user.');
    }
  };

  const handleRecoverySubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await apiClient.post('/api/recovery/submit/', {
        username,
        answer_1: answer1,
        answer_2: answer2,
        new_password: newPassword,
      });
      setSuccess('Password has been reset successfully! You can now log in.');
      setTimeout(() => {
        onNavigateToLogin();
      }, 3000);
    } catch (err) {
      setError(err.response?.data?.error || 'Recovery failed. Please check your answers.');
    }
  };
  
  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
      <div className="flex items-center text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">
        <img src="/axon.png" alt="Axon logo" className="h-24 w-24 mr-4"/>
        <h1>Recover Identity</h1>
      </div>
      
      {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
      {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>}

      {step === 1 && (
        <form onSubmit={handleUsernameSubmit}>
            <p className="text-gray-400 mb-4">Enter your username to begin the recovery process.</p>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="username">Username</label>
                <input id="username" type="text" value={username} onChange={e => setUsername(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
            <div className="flex items-center justify-between">
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded w-full">
                    Continue
                </button>
            </div>
        </form>
      )}

      {step === 2 && questions && (
        <form onSubmit={handleRecoverySubmit}>
            <p className="text-gray-400 mb-4">Answer your two security questions to set a new password.</p>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2">{questions.security_question_1}</label>
                <input type="password" value={answer1} onChange={e => setAnswer1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
            <div className="mb-4">
                <label className="block text-gray-300 text-sm font-bold mb-2">{questions.security_question_2}</label>
                <input type="password" value={answer2} onChange={e => setAnswer2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
            <div className="mb-6">
                <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="new_password">New Password</label>
                <input id="new_password" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"/>
            </div>
             <div className="flex items-center justify-between">
                <button type="submit" className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded w-full">
                    Reset Password
                </button>
            </div>
        </form>
      )}
       <button onClick={onNavigateToLogin} className="inline-block align-baseline font-bold text-sm text-blue-400 hover:text-blue-500 mt-4" type="button">
        Back to Login
      </button>
    </div>
  );
};

export default RecoveryScreen;
