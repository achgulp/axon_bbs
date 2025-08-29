// Full path: axon_bbs/frontend/src/components/AppletView.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import AppletRunner from './AppletRunner'; // NEW

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

const AppletView = () => {
  const [applets, setApplets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [runningApplet, setRunningApplet] = useState(null); // NEW

  useEffect(() => {
    // Only fetch applets if we are in the list view
    if (!runningApplet) {
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
  }, [runningApplet]); // Re-fetch when we return to the list view

  // If an applet is selected to run, render the AppletRunner
  if (runningApplet) {
    return <AppletRunner applet={runningApplet} onBack={() => setRunningApplet(null)} />;
  }

  // Otherwise, render the list of available applets
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
                <h3 className="font-bold text-lg text-gray-200">{applet.name}</h3>
                <p className="text-sm text-gray-400">{applet.description}</p>
              </div>
              <button 
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                onClick={() => setRunningApplet(applet)} // UPDATED
              >
                Launch
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AppletView;
