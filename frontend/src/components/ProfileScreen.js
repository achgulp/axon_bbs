// Full path: axon_bbs/frontend/src/components/ProfileScreen.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

const ProfileScreen = () => {
  const [profile, setProfile] = useState(null);
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchProfile = useCallback(() => {
    setIsLoading(true);
    apiClient.get('/api/user/profile/')
      .then(response => {
        setProfile(response.data);
        setNickname(response.data.nickname || '');
      })
      .catch(err => {
        console.error("Failed to fetch profile:", err);
        setError("Could not load your profile data.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleNicknameChange = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);
    try {
      await apiClient.post('/api/user/nickname/', { nickname });
      setSuccess('Nickname updated successfully!');
      // Refresh profile data to confirm change
      fetchProfile();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update nickname.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !profile) {
    return <div>Loading profile...</div>;
  }

  return (
    <div>
      <Header text="User Profile" />
      {error && <div className="bg-red-800 border border-red-600 text-red-200 p-3 rounded mb-4">{error}</div>}
      {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>}
      
      <div className="bg-gray-800 p-4 rounded mb-6 border border-gray-700">
        <div className="mb-4">
          <label className="block text-gray-400 text-sm font-bold mb-2">Username</label>
          <p className="text-gray-200">{profile?.username}</p>
        </div>
        <div className="mb-6">
          <label className="block text-gray-400 text-sm font-bold mb-2">Public Key</label>
          <textarea
            readOnly
            value={profile?.pubkey || 'No public key generated yet.'}
            className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-900 text-gray-400 leading-tight focus:outline-none focus:shadow-outline font-mono text-xs"
            rows="6"
          />
        </div>

        <form onSubmit={handleNicknameChange}>
          <label className="block text-gray-300 text-sm font-bold mb-2" htmlFor="nickname">
            Nickname
          </label>
          <p className="text-gray-400 text-xs italic mb-2">This name will be displayed next to your public posts.</p>
          <div className="flex items-center gap-4">
            <input
              id="nickname"
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="Enter your desired nickname"
              className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isLoading || nickname === (profile?.nickname || '')}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500"
            >
              {isLoading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileScreen;
