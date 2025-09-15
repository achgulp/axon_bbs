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


// Full path: axon_bbs/frontend/src/components/ModerationDashboard.js
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

const ModerationDashboard = () => {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchReports = useCallback(() => {
    setIsLoading(true);
    setError('');
    apiClient.get('/api/moderation/queue/')
      .then(response => {
        setReports(response.data);
      })
      .catch(err => {
        console.error("Failed to fetch moderation queue:", err);
        setError("Could not load the moderation queue. You may not have permission to view this page.");
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleReview = async (reportId, action) => {
    try {
      await apiClient.post(`/api/moderation/review/${reportId}/`, { action });
      // Remove the reviewed report from the list for immediate UI feedback
      setReports(prevReports => prevReports.filter(report => report.id !== reportId));
    } catch (err) {
      console.error(`Failed to ${action} report:`, err);
      alert(`Could not ${action} the report. Please try again.`);
    }
  };

  return (
    <div>
      <Header text="Moderation Dashboard" />
      {isLoading ? (
        <div>Loading pending reports...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : reports.length === 0 ? (
        <p className="text-gray-400">The moderation queue is empty. Good job!</p>
      ) : (
        <div className="space-y-6">
          {reports.map(report => (
            <div key={report.id} className="bg-gray-800 p-4 rounded border border-gray-700">
              <div className="border-b border-gray-600 pb-3 mb-3">
                <p className="text-sm text-gray-400">
                  Reported by: <span className="font-semibold text-gray-300">{report.reporting_user}</span> on {new Date(report.created_at).toLocaleString()}
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
                <button
                  onClick={() => handleReview(report.id, 'reject')}
                  className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded"
                >
                  Reject Report
                </button>
                <button
                  onClick={() => handleReview(report.id, 'approve')}
                  className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
                >
                  Approve (Delete Message)
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ModerationDashboard;
