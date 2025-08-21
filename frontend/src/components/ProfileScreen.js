// Full path: axon_bbs/frontend/src/components/ProfileScreen.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const SubHeader = ({ text }) => <h3 className="text-lg font-semibold text-gray-300 mb-3">{text}</h3>;

const ProfileScreen = () => {
  const [profile, setProfile] = useState(null);
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const [exportPassword, setExportPassword] = useState('');
  const [importAccountPassword, setImportAccountPassword] = useState('');
  const [importKeyPassword, setImportKeyPassword] = useState('');
  const [keyFile, setKeyFile] = useState(null);
  const [avatarFile, setAvatarFile] = useState(null);

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
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => { fetchProfile(); }, [fetchProfile]);

  const handleNicknameChange = async (e) => {
    e.preventDefault();
    setError(''); setSuccess(''); setIsLoading(true);
    try {
      await apiClient.post('/api/user/nickname/', { nickname });
      setSuccess('Nickname updated successfully!');
      fetchProfile();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update nickname.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportKey = async (e) => {
    e.preventDefault();
    setError(''); setSuccess(''); setIsLoading(true);
    try {
      const response = await apiClient.post('/api/identity/export/', { password: exportPassword }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${profile.username}_axon_key_encrypted.pem`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      setSuccess('Encrypted private key has been downloaded.');
      setExportPassword('');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to export key. Check your password.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleImportKey = async (e) => {
    e.preventDefault();
    if (!keyFile) { setError('Please select a key file to import.'); return; }
    setError(''); setSuccess(''); setIsLoading(true);
    const formData = new FormData();
    formData.append('key_file', keyFile);
    formData.append('account_password', importAccountPassword);
    if (importKeyPassword) {
      formData.append('key_file_password', importKeyPassword);
    }
    formData.append('name', 'default');
    try {
      await apiClient.post('/api/identity/import/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setSuccess('Key imported successfully! Your profile has been updated.');
      setImportAccountPassword('');
      setImportKeyPassword('');
      setKeyFile(null);
      fetchProfile();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to import key. Check your passwords and file.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAvatarUpload = async (e) => {
    e.preventDefault();
    if (!avatarFile) { setError('Please select an image file to upload.'); return; }
    setError(''); setSuccess(''); setIsLoading(true);
    const formData = new FormData();
    formData.append('avatar', avatarFile);
    try {
      await apiClient.post('/api/user/avatar/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setSuccess('Avatar updated successfully!');
      setAvatarFile(null);
      fetchProfile(); // Refresh profile to show new avatar
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload avatar.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !profile) { return <div>Loading profile...</div>; }

  return (
    <div>
      <Header text="User Profile" />
      {error && <div className="bg-red-800 border border-red-600 text-red-200 p-3 rounded mb-4">{error}</div>}
      {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4">{success}</div>}
      
      <div className="bg-gray-800 p-4 rounded mb-6 border border-gray-700">
        <div className="flex items-start gap-4 mb-4">
          <img src={profile?.avatar_url || '/default_avatar.png'} alt="Avatar" className="w-16 h-16 rounded-full bg-gray-700 border-2 border-gray-600" />
          <div>
            <div className="mb-2">
              <label className="block text-gray-400 text-sm font-bold">Username</label>
              <p className="text-gray-200 text-lg">{profile?.username}</p>
            </div>
            <form onSubmit={handleNicknameChange}>
              <label className="block text-gray-300 text-sm font-bold mb-1" htmlFor="nickname">Nickname</label>
              <div className="flex items-center gap-4">
                <input id="nickname" type="text" value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="Enter your desired nickname" className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <button type="submit" disabled={isLoading || nickname === (profile?.nickname || '')} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500">
                  {isLoading ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
        <div className="mb-6">
          <label className="block text-gray-400 text-sm font-bold mb-2">Public Key</label>
          <textarea readOnly value={profile?.pubkey || 'No public key generated or imported yet.'} className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-900 text-gray-400 leading-tight focus:outline-none focus:shadow-outline font-mono text-xs" rows="6" />
        </div>
      </div>

      <div className="bg-gray-800 p-4 rounded border border-gray-700">
        <SubHeader text="Manage Identity & Avatar" />
        <div className="mb-6 border-b border-gray-700 pb-6">
          <h4 className="font-bold text-gray-300 mb-2">Change Your Avatar (32x32)</h4>
           <form onSubmit={handleAvatarUpload} className="flex items-center gap-4">
            <input type="file" onChange={e => setAvatarFile(e.target.files[0])} accept="image/png, image/jpeg, image/gif" required className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"/>
            <button type="submit" disabled={isLoading || !avatarFile} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500 whitespace-nowrap">
              Upload
            </button>
          </form>
        </div>
        <div className="mb-6 border-b border-gray-700 pb-6">
          <h4 className="font-bold text-gray-300 mb-2">Backup Your Private Key (Encrypted)</h4>
          <p className="text-gray-400 text-xs italic mb-2">Enter your current account password. The downloaded .pem file will be encrypted with this password.</p>
          <form onSubmit={handleExportKey} className="flex items-center gap-4">
            <input type="password" value={exportPassword} onChange={e => setExportPassword(e.target.value)} placeholder="Enter current account password" required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
            <button type="submit" disabled={isLoading || !exportPassword} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500 whitespace-nowrap">
              Download Key
            </button>
          </form>
        </div>
        <div>
          <h4 className="font-bold text-gray-300 mb-2">Import an Existing Key</h4>
          <p className="text-gray-400 text-xs italic mb-2">Upload a PEM file containing a private key. This will overwrite your current key.</p>
          <form onSubmit={handleImportKey}>
            <div className="mb-4">
              <label className="block text-gray-300 text-sm font-bold mb-2">Key File (.pem)</label>
              <input type="file" onChange={e => setKeyFile(e.target.files[0])} accept=".pem" required className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"/>
            </div>
            <div className="mb-4">
              <label className="block text-gray-300 text-sm font-bold mb-2">Current Account Password</label>
              <input type="password" value={importAccountPassword} onChange={e => setImportAccountPassword(e.target.value)} placeholder="Enter your account password" required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="mb-4">
              <label className="block text-gray-300 text-sm font-bold mb-2">Password for Key File (if it's encrypted)</label>
              <input type="password" value={importKeyPassword} onChange={e => setImportKeyPassword(e.target.value)} placeholder="Leave blank if not encrypted" className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="text-right">
              <button type="submit" disabled={isLoading || !importAccountPassword || !keyFile} className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500">
                Import and Overwrite Key
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ProfileScreen;
