// axon_bbs/frontend/src/components/LoginScreen.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

const LoginScreen = ({ onLogin, onNavigateToRegister }) => {
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
      localStorage.setItem('token', response.data.access); // Store access token
      onLogin(response.data.access);
    } catch (err) {
      setError('Invalid username or password.');
      console.error(err);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
      <div className="text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">Login</div>
      <form onSubmit={handleLogin}>
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="username">
            Username
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="mb-6">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password">
            Password
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
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
        </div>
      </form>
    </div>
  );
};

export default LoginScreen;
