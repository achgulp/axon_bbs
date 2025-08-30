// Full path: axon_bbs/frontend/src/components/AppletView.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import AppletRunner from './AppletRunner';
import HighScoreBoard from './HighScoreBoard';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
// UPDATED: Added onLaunchGame prop
const AppletView = ({ onLaunchGame }) => {
  const [applets, setApplets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [runningApplet, setRunningApplet] = useState(null);
  const [viewingScoresFor, setViewingScoresFor] = useState(null);

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
      onLaunchGame(applet); // Notify App.js about the last played game
    }
    setRunningApplet(applet);
  };

  if (runningApplet) {
    return <AppletRunner applet={runningApplet} onBack={() => setRunningApplet(null)} />;
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
      ) : applets.length === 0 ? (
        <div className="bg-gray-800 p-4 rounded border border-gray-700 text-center text-gray-400">
          <p>No applets are currently installed on this instance.</p>
    
          <p className="text-sm mt-2">Applets can be added by the system administrator.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {applets.map(applet => (
            <div key={applet.id} className="bg-gray-800 p-4 rounded border border-gray-700 flex justify-between items-center">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="font-bold text-lg text-gray-200">{applet.name}</h3>
                  {applet.category_name && <span className="text-xs font-semibold bg-gray-700 text-gray-300 px-2 py-1 rounded-full">{applet.category_name}</span>}
                </div>
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
