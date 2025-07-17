// axon_bbs/frontend/src/components/RegisterScreen.js
import React, { useState } from 'react';
import apiClient from '../apiClient';

const RegisterScreen = ({ onRegisterSuccess, onNavigateToLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [error, setError] = useState('');

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
      });
      // On successful registration, automatically navigate to the login screen
      onRegisterSuccess();
    } catch (err) {
      if (err.response && err.response.data && err.response.data.username) {
        setError(err.response.data.username[0]);
      } else {
        setError('An unexpected error occurred during registration.');
      }
      console.error(err);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-gray-800 rounded-lg">
      <div className="text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">Register</div>
      <form onSubmit={handleRegister}>
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
        <div className="mb-4">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password">
            Password
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:shadow-outline"
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <div className="mb-6">
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="password2">
            Confirm Password
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            id="password2"
            type="password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            required
          />
        </div>
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

