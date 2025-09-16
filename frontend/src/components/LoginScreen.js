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


// Full path: axon_bbs/frontend/src/components/LoginScreen.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

const LoginScreen = ({ onLogin, onNavigateToRegister, onNavigateToRecovery }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await apiClient.post('/api/token/', {
        username,
        password,
      });
      localStorage.setItem('token', response.data.access);
      onLogin(response.data.access);
    } catch (err) {
      setError('Invalid username or password.');
      console.error(err);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
      <div className="flex items-center text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">
        <img src="/axon.png" alt="Axon logo" className="h-24 w-24 mr-4"/>
        <h1>Login</h1>
      </div>
      <form onSubmit={handleLogin}>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="username">
            Username
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"
            id="username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required
          />
        </div>
        <div className="mb-6">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password">
            Password
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
          />
        </div>
        {error && <p className="text-red-500 text-xs italic mb-4">{error}</p>}
        <div className="flex flex-col items-center justify-between">
          <button
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full"
            type="submit"
          >
            Sign In
          </button>
          <button
            onClick={onNavigateToRegister}
            className="inline-block align-baseline font-bold text-sm text-blue-400 hover:text-blue-500 mt-4"
            type="button"
          >
            Don't have an account? Register
          </button>
          <button
            onClick={onNavigateToRecovery}
            className="inline-block align-baseline font-bold text-sm text-gray-400 hover:text-gray-300 mt-2"
            type="button"
          >
            Forgot Password?
          </button>
        </div>
      </form>
    </div>
  );
};

export default LoginScreen;
