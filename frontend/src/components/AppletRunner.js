// Full path: axon_bbs/frontend/src/components/AppletRunner.js
import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../apiClient';

const AppletRunner = ({ applet, onBack }) => {
  const [appletCode, setAppletCode] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [profile, setProfile] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    apiClient.get('/api/user/profile/')
      .then(response => setProfile(response.data))
      .catch(err => console.error("Could not fetch profile for applet.", err));
  }, []);

  useEffect(() => {
    const handleMessage = async (event) => {
      if (event.source !== iframeRef.current?.contentWindow) return;

      const { command, payload, requestId } = event.data;
      
      let response = { command: `response_${command}`, requestId, payload: null, error: null };

      try {
        switch (command) {
          case 'getUserInfo':
            if (profile) {
              response.payload = profile;
            } else {
              const freshProfile = await apiClient.get('/api/user/profile/');
              setProfile(freshProfile.data);
              response.payload = freshProfile.data;
            }
            break;
          // Handlers for getData and saveData will be added here
          default:
            break;
        }
      } catch (e) {
        response.error = e.message;
      }
      
      iframeRef.current.contentWindow.postMessage(response, '*');
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [profile]);

  useEffect(() => {
    if (!applet?.code_manifest?.content_hash) {
      setError("Applet has an invalid code manifest.");
      setIsLoading(false);
      return;
    }
    const contentHash = applet.code_manifest.content_hash;
    setIsLoading(true);
    setError('');
    apiClient.get(`/api/content/download/${contentHash}/`)
      .then(response => {
        setAppletCode(response.data);
      })
      .catch(err => {
        console.error("Failed to download applet code:", err);
        setError(err.response?.data?.error || "Could not download applet code.");
      })
      .finally(() => setIsLoading(false));
  }, [applet]);

  const getIframeContent = () => {
    if (!appletCode) return '';
    
    const checksum = applet?.code_manifest?.content_hash || 'N/A';
    
    // UPDATED: This structure fixes the race condition for the checksum.
    // The applet's code is now wrapped in a DOMContentLoaded event listener.
    // This ensures the `window` object is fully available before the applet script runs.
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${applet.name}</title>
        </head>
        <body>
          <div id="applet-root"></div>
          <script>
            window.BBS_APPLET_CHECKSUM = '${checksum}';
            document.addEventListener("DOMContentLoaded", function() {
              try {
                ${appletCode}
              } catch (e) {
                const root = document.getElementById('applet-root');
                if (root) {
                  root.innerHTML = '<p style="color: red; font-family: monospace;">Applet Failed to Execute: ' + e.message + '</p>';
                }
                console.error("Applet execution error:", e);
              }
            });
          </script>
        </body>
      </html>
    `;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-200">${applet.name}</h2>
        <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
          ← Back to Applets
        </button>
      </div>
      <div className="w-full h-[75vh] bg-gray-900 border border-gray-700 rounded overflow-hidden">
        {isLoading && <div className="p-4">Loading applet code...</div>}
        {error && <div className="p-4 text-red-500">{error}</div>}
        {!isLoading && !error && (
          <iframe
            ref={iframeRef}
            title={applet.name}
            srcDoc={getIframeContent()}
            className="w-full h-full"
            sandbox="allow-scripts"
          />
        )}
      </div>
    </div>
  );
};

export default AppletRunner;


