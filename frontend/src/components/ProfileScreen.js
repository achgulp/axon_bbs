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


// Full path: axon_bbs/frontend/src/components/ProfileScreen.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';
import ContactModeratorsModal from './ContactModeratorsModal'; // MODIFIED: Import the new modal

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const SubHeader = ({ text }) => <h3 className="text-lg font-semibold text-gray-300 mb-3">{text}</h3>;

const ProfileScreen = () => {
  const [profile, setProfile] = useState(null);
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [currentPasswordForReset, setCurrentPasswordForReset] = useState('');
  const [sq1, setSq1] = useState('');
  const [sa1, setSa1] = useState('');
  const [sq2, setSq2] = useState('');
  const [sa2, setSa2] = useState('');
  const [exportPassword, setExportPassword] = useState('');

  const [timezones, setTimezones] = useState([]);
  const [selectedTimezone, setSelectedTimezone] = useState('');
  const [avatarFile, setAvatarFile] = useState(null);
  
  // NEW: State for the contact modal
  const [showContactModal, setShowContactModal] = useState(false);

  const fetchProfile = useCallback(() => {
    setIsLoading(true);
    apiClient.get('/api/user/profile/')
      .then(response => {
        setProfile(response.data);
        setNickname(response.data.nickname || '');
        setSelectedTimezone(response.data.timezone || 'UTC');
      })
      .catch(err => {
        console.error("Failed to fetch profile:", err);
        setError("Could not load your profile data.");
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => { 
    fetchProfile(); 
    setTimezones(Intl.supportedValuesOf('timeZone'));
  }, [fetchProfile]);

  const handleNicknameChange = async (e) => {
    e.preventDefault();
    setError(''); setSuccess(''); setIsLoading(true);
    try {
      const response = await apiClient.post('/api/user/nickname/', { nickname });
      setSuccess(response.data.status || 'Nickname update submitted for approval!');
      fetchProfile();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update nickname.');
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
      const response = await apiClient.post('/api/user/avatar/', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setSuccess(response.data.status || 'Avatar update submitted for approval!');
      setAvatarFile(null);
      e.target.reset();
      fetchProfile();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload avatar.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmNewPassword) {
        setError("New passwords do not match.");
        return;
    }
    setError(''); setSuccess(''); setIsLoading(true);
    try {
        await apiClient.post('/api/user/change_password/', { old_password: oldPassword, new_password: newPassword });
        setSuccess('Password changed successfully!');
        setOldPassword('');
        setNewPassword('');
        setConfirmNewPassword('');
    } catch (err) {
        setError(err.response?.data?.error || 'Failed to change password.');
    } finally {
        setIsLoading(false);
    }
  };

  const handleResetSecurityQuestions = async (e) => {
    e.preventDefault();
    setError(''); setSuccess(''); setIsLoading(true);
    try {
        await apiClient.post('/api/user/reset_security_questions/', {
            current_password: currentPasswordForReset,
            security_question_1: sq1,
            security_answer_1: sa1,
            security_question_2: sq2,
            security_answer_2: sa2,
        });
        setSuccess('Security questions have been reset successfully!');
        setCurrentPasswordForReset('');
        setSq1(''); setSa1('');
        setSq2(''); setSa2('');
    } catch (err) {
        setError(err.response?.data?.error || 'Failed to reset security questions.');
    } finally {
        setIsLoading(false);
    }
  };

  const handleTimezoneChange = async (e) => {
    e.preventDefault();
    setError(''); setSuccess(''); setIsLoading(true);
    try {
        await apiClient.post('/api/user/timezone/', { timezone: selectedTimezone });
        setSuccess('Timezone updated successfully!');
        fetchProfile();
    } catch(err) {
        setError(err.response?.data?.error || 'Failed to update timezone.');
    } finally {
        setIsLoading(false);
    }
  };

  const handleExportIdentity = async (e) => {
    e.preventDefault();
    if (!exportPassword) {
      setError("You must enter your current password to export your key.");
      return;
    }
    setError(''); setSuccess(''); setIsLoading(true);
    try {
      const response = await apiClient.post('/api/identity/export/', { password: exportPassword }, { responseType: 'blob' });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${profile.username}_axon_identity_encrypted.pem`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setSuccess('Your encrypted identity key has been downloaded.');
      setExportPassword('');

    } catch (err) {
        const errorText = await err.response?.data?.text();
        let errorJson = {};
        try { errorJson = JSON.parse(errorText); } catch {}
        setError(errorJson?.error || 'Failed to export identity. Please check your password.');
    } finally {
        setIsLoading(false);
    }
  };

  if (isLoading && !profile) { return <div>Loading profile...</div>; }

  return (
    <div>
      <ContactModeratorsModal show={showContactModal} onClose={() => setShowContactModal(false)} />
      <Header text="User Profile" />
      {error && <div className="bg-red-800 border border-red-600 text-red-200 p-3 rounded mb-4" role="alert">{error}</div>}
      {success && <div className="bg-green-800 border border-green-600 text-green-200 p-3 rounded mb-4" role="alert">{success}</div>}
      
      <div className="bg-gray-800 p-4 rounded mb-6 border border-gray-700">
        <div className="flex items-start gap-4 mb-4">
          <img src={profile?.avatar_url || '/default_avatar.png'} alt="Avatar" className="w-32 h-32 rounded-full bg-gray-700 border-2 border-gray-600" />
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
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <SubHeader text="Manage Avatar" />
          <p className="text-gray-400 text-xs italic mb-2">Upload a new avatar. PNG, JPG, or GIF, max 1MB. Will be resized to 128x128.</p>
          <form onSubmit={handleAvatarUpload} className="flex items-center gap-4">
            <input type="file" onChange={e => setAvatarFile(e.target.files[0])} accept="image/png, image/jpeg, image/gif" required className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"/>
            <button type="submit" disabled={isLoading || !avatarFile} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500 whitespace-nowrap">
              Upload
            </button>
          </form>
        </div>

        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <SubHeader text="Export Identity" />
          <p className="text-gray-400 text-xs italic mb-2">Download a backup of your private key, encrypted with your password.</p>
          <form onSubmit={handleExportIdentity} className="flex items-center gap-4">
            <input type="password" value={exportPassword} onChange={e => setExportPassword(e.target.value)} placeholder="Enter current password" required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            <button type="submit" disabled={isLoading || !exportPassword} className="bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-gray-500 whitespace-nowrap">
              Export Key
            </button>
          </form>
        </div>
        
        {/* MODIFIED: Added Contact Moderators button */}
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <SubHeader text="Support" />
            <p className="text-gray-400 text-xs italic mb-2">Have a general question or concern for the moderators?</p>
            <button onClick={() => setShowContactModal(true)} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded w-full">
                Contact Moderators
            </button>
        </div>

        <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <SubHeader text="Display Timezone" />
            <form onSubmit={handleTimezoneChange} className="flex items-center gap-4">
                <select value={selectedTimezone} onChange={e => setSelectedTimezone(e.target.value)} className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {timezones.map(tz => <option key={tz} value={tz}>{tz}</option>)}
                </select>
                <button type="submit" disabled={isLoading || selectedTimezone === (profile?.timezone || 'UTC')} className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-500">Save</button>
            </form>
        </div>

        <div className="bg-gray-800 p-4 rounded border border-gray-700 md:col-span-2">
            <SubHeader text="Change Password" />
            <form onSubmit={handleChangePassword}>
                <div className="grid md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">Current Password</label>
                        <input type="password" value={oldPassword} onChange={e => setOldPassword(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">New Password</label>
                        <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">Confirm New Password</label>
                        <input type="password" value={confirmNewPassword} onChange={e => setConfirmNewPassword(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                </div>
                <div className="text-right mt-4">
                    <button type="submit" disabled={isLoading} className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-500">Update Password</button>
                </div>
            </form>
        </div>

        <div className="bg-gray-800 p-4 rounded border border-gray-700 md:col-span-2">
            <SubHeader text="Reset Security Questions" />
            <p className="text-gray-400 text-xs italic mb-2">You must provide your current password to reset your security questions.</p>
            <form onSubmit={handleResetSecurityQuestions}>
                <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-bold mb-2">Current Password</label>
                    <input type="password" value={currentPasswordForReset} onChange={e => setCurrentPasswordForReset(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                </div>
                <div className="grid md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">New Security Question 1</label>
                        <input type="text" placeholder="e.g., What was your first pet's name?" value={sq1} onChange={e => setSq1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"/>
                        <input type="password" placeholder="Answer 1" value={sa1} onChange={e => setSa1(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                    </div>
                    <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">New Security Question 2</label>
                        <input type="text" placeholder="e.g., What city were you born in?" value={sq2} onChange={e => setSq2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"/>
                        <input type="password" placeholder="Answer 2" value={sa2} onChange={e => setSa2(e.target.value)} required className="shadow appearance-none border rounded w-full py-2 px-3 bg-gray-700 text-gray-200 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"/>
                    </div>
                </div>
                <div className="text-right mt-4">
                    <button type="submit" disabled={isLoading} className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-500">Reset Questions</button>
                </div>
            </form>
        </div>
      </div>
    </div>
  );
};

export default ProfileScreen;
