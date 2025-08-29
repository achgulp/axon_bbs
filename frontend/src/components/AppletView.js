// Full path: axon_bbs/frontend/src/components/AppletView.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;

const AppletView = () => {
  const [applets, setApplets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
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
  }, []);

  if (isLoading) {
    return <div>Loading Applets...</div>;
  }

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div>
      <Header text="Applet Browser" />
      {applets.length === 0 ? (
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
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:bg-gray-500"
                // The onClick handler will be implemented in the next step
                onClick={() => alert(`Launching "${applet.name}"... (functionality to be implemented)`)}
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
