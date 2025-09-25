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


// Full path: axon_bbs/frontend/src/components/ModerationDashboard.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';
import AuthenticatedImage from './AuthenticatedImage';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const ModerationDashboard = ({ displayTimezone }) => {
  const [reports, setReports] = useState([]);
  const [profileUpdates, setProfileUpdates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('reports');
  const fetchReports = useCallback(() => {
    apiClient.get('/api/moderation/queue/')
      .then(response => setReports(response.data))
      .catch(err => {
        console.error("Failed to fetch moderation queue:", err);
        setError("Could not load the message report queue.");
      });
  }, []);
  const fetchProfileUpdates = useCallback(() => {
    apiClient.get('/api/moderation/profile_queue/')
      .then(response => setProfileUpdates(response.data))
      .catch(err => {
        console.error("Failed to fetch profile update queue:", err);
        setError("Could not load the profile update queue.");
      });
  }, []);
useEffect(() => {
    setIsLoading(true);
    const fetchAll = async () => {
        await Promise.all([
            fetchReports(),
            fetchProfileUpdates()
        ]);
        setIsLoading(false);
    };
    fetchAll();
  }, [fetchReports, fetchProfileUpdates]);
  const handleReviewReport = async (reportId, action) => {
    try {
      await apiClient.post(`/api/moderation/review/${reportId}/`, { action });
      setReports(prev => prev.filter(report => report.id !== reportId));
    } catch (err) {
      console.error(`Failed to ${action} report:`, err);
      alert(`Could not ${action} the report. Please try again.`);
    }
  };
  const handleReviewProfile = async (actionId, action) => {
      try {
          await apiClient.post(`/api/moderation/profile_review/${actionId}/`, { action });
          setProfileUpdates(prev => prev.filter(update => update.id !== actionId));
      } catch(err) {
          console.error(`Failed to ${action} profile update:`, err);
          alert(`Could not ${action} the profile update.`);
      }
  };

  const renderMessageReports = () => (
    reports.length === 0 ? (
        <p className="text-gray-400">The message report queue is empty. Good job!</p>
    ) : (
        <div className="space-y-6">
            {reports.map(report => (
                <div key={report.id} className="bg-gray-800 p-4 rounded border border-gray-700">
                    <div className="border-b border-gray-600 pb-3 mb-3">
                    <p className="text-sm text-gray-400">
                        Reported by: <span className="font-semibold text-gray-300">{report.reporting_user}</span> on {new Date(report.created_at).toLocaleString([], { timeZone: displayTimezone })}
                    </p>
                    <p className="text-sm text-gray-400">
                    Reporter's Comment: <span className="text-yellow-400 italic">"{report.comment || 'No comment provided.'}"</span>
                    </p>
                </div>
                <div className="bg-gray-900 p-3 rounded">
                    <p className="text-sm text-gray-400">
                        Original Author: <span className="font-semibold text-gray-300">{report.reported_message.author_display}</span>
                    </p>
                    <p className="text-sm text-gray-400">
                        Subject: <span className="font-semibold text-gray-300">{report.reported_message.subject}</span>
                    </p>
                    <p className="text-gray-300 whitespace-pre-wrap mt-2 p-2 border border-dashed border-gray-600 rounded">
                        {report.reported_message.body}
                    </p>
                </div>
                <div className="flex justify-end gap-4 mt-4">
                    <button onClick={() => handleReviewReport(report.id, 'reject')} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">
                        Reject Report
                    </button>
                    <button onClick={() => handleReviewReport(report.id, 'approve')} className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
                        Approve (Delete Message)
                    </button>
                </div>
                </div>
            ))}
        </div>
    )
  );
  const renderProfileApprovals = () => (
    profileUpdates.length === 0 ? (
        <p className="text-gray-400">The profile approval queue is empty.</p>
    ) : (
        <div className="space-y-6">
            {profileUpdates.map(update => (
                <div key={update.id} className="bg-gray-800 p-4 rounded border border-gray-700">
                    <div className="border-b border-gray-600 pb-3 mb-3">
                        <p className="text-sm text-gray-400">
                            {/* --- BUG FIX START: Use optional chaining (?.) to prevent crash if user_info is null --- */}
                            Request by: <span className="font-semibold text-gray-300">{update.user_info?.username}</span> on {new Date(update.created_at).toLocaleString([], { timeZone: displayTimezone })}
                        </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <h4 className="font-bold text-gray-300 mb-2">Nickname Change</h4>
                            <p className="text-sm text-gray-400">From: <span className="text-gray-200">{update.user_info?.current_nickname || '[None]'}</span></p>
                            <p className="text-sm text-green-400">To: <span className="font-bold">{update.action_details.nickname}</span></p>
                        </div>
                        <div>
                            <h4 className="font-bold text-gray-300 mb-2">Avatar Change</h4>
                            {update.pending_avatar_url ? (
                                <div>
                                    <p className="text-sm text-yellow-400 mb-2">New avatar for review:</p>
                                    <AuthenticatedImage 
                                        src={update.pending_avatar_url} 
                                        alt="Pending avatar" 
                                        className="w-32 h-32 rounded-full border-2 border-yellow-500" 
                                    />
                                </div>
                            ) : (
                                <p className="text-sm text-gray-400">No new avatar submitted.</p>
                            )}
                        </div>
                    </div>
                    {/* --- BUG FIX END --- */}
                    <div className="flex justify-end gap-4 mt-4">
                        <button onClick={() => handleReviewProfile(update.id, 'deny')} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">
                            Deny
                        </button>
                        <button onClick={() => handleReviewProfile(update.id, 'approve')} className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
                            Approve
                        </button>
                    </div>
                </div>
            ))}
        </div>
    )
  );
return (
    <div>
      <Header text="Moderation Dashboard" />
      <div className="mb-4 border-b border-gray-600">
        <nav className="flex space-x-4">
            <button onClick={() => setActiveTab('reports')} className={`py-2 px-4 font-semibold ${activeTab === 'reports' ? 'text-white border-b-2 border-blue-500' : 'text-gray-400 hover:text-white'}`}>
                Message Reports ({reports.length})
            </button>
            <button onClick={() => setActiveTab('profiles')} className={`py-2 px-4 font-semibold ${activeTab === 'profiles' ? 'text-white border-b-2 border-blue-500' : 'text-gray-400 hover:text-white'}`}>
                Profile Approvals ({profileUpdates.length})
            </button>
        </nav>
      </div>
      {isLoading ? (
        <div>Loading moderation queues...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : (
        <div>
            {activeTab === 'reports' && renderMessageReports()}
            {activeTab === 'profiles' && renderProfileApprovals()}
        </div>
      )}
    </div>
  );
};

export default ModerationDashboard;
