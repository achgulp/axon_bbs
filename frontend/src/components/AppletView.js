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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.


// Full path: axon_bbs/frontend/src/components/AppletView.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import AppletRunner from './AppletRunner';
import HighScoreBoard from './HighScoreBoard';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

const AppletView = ({ onLaunchGame }) => {
  const [applets, setApplets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [runningApplet, setRunningApplet] = useState(null);
  const [viewingScoresFor, setViewingScoresFor] = useState(null);
  // NEW: A counter to force re-mounting the AppletRunner
  const [launchCounter, setLaunchCounter] = useState(0);

  useEffect(() => {
    if (!runningApplet && !viewingScoresFor) {
      setIsLoading(true);
      apiClient.get('/api/applets/')
        .then(response => {
          setApplets(response.data);
        })
        .catch(err => {
          console.error("Failed to fetch applets:", err);
          setError("Could not load applets from the server.");
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [runningApplet, viewingScoresFor]);

  const handleLaunch = (applet) => {
    if (applet.category_name?.toLowerCase() === 'game') {
      onLaunchGame(applet);
    }
    // Increment the counter to generate a new key
    setLaunchCounter(prev => prev + 1);
    setRunningApplet(applet);
  };

  if (runningApplet) {
    // UPDATED: The key prop is now a combination of the applet ID and the launch counter.
    // This guarantees React will create a new component instance every single time.
    return <AppletRunner key={`${runningApplet.id}-${launchCounter}`} applet={runningApplet} onBack={() => setRunningApplet(null)} />;
  }

  if (viewingScoresFor) {
    return <HighScoreBoard applet={viewingScoresFor} onBack={() => setViewingScoresFor(null)} />;
  }

  return (
    <div>
      <Header text="Applet Browser" />
      {isLoading ? (
        <div>Loading Applets...</div>
      ) : error ? (
        <div className="text-red-500">{error}</div>
      ) : (
        <div className="space-y-4">
          {applets.map(applet => (
            <div key={applet.id} className="bg-gray-800 p-4 rounded border border-gray-700 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg text-gray-200">{applet.name}</h3>
                <p className="text-sm text-gray-400 mt-1">{applet.description}</p>
              </div>
              <div className="flex gap-2">
                {applet.category_name?.toLowerCase() === 'game' && (
                  <button
                    className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded"
                    onClick={() => setViewingScoresFor(applet)}
                  >
                    Scores
                  </button>
                )}
                <button
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                  onClick={() => handleLaunch(applet)}
                >
                  Launch
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AppletView;

