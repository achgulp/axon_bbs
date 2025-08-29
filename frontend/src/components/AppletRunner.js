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
      // Security: Ensure the message is from our iframe
      if (event.source !== iframeRef.current?.contentWindow) return;

      const { command, payload, requestId } = event.data;
      
      let response = { command: `response_${command}`, requestId, payload: null, error: null };

      try {
        switch (command) {
          case 'getUserInfo':
            if (profile) {
              response.payload = profile;
            } else {
              // Fetch profile on demand if not already loaded
              const freshProfile = await apiClient.get('/api/user/profile/');
              setProfile(freshProfile.data);
              response.payload = freshProfile.data;
            }
            break;

          // UPDATED: Added handler for the 'getData' command from the applet API.
          case 'getData':
            // This currently returns an empty object because the backend API endpoint
            // for applet data storage has not been implemented yet.
            // When implemented, this will fetch user-specific data for this applet.
            try {
                // NOTE: The endpoint `/api/applets/${applet.id}/data/` needs to be created on the backend.
                const dataResponse = await apiClient.get(`/api/applets/${applet.id}/data/`);
                response.payload = dataResponse.data;
            } catch (apiError) {
                if (apiError.response && apiError.response.status === 404) {
                    // It's not an error if no data has been saved yet. Return an empty object.
                    response.payload = {}; 
                } else {
                    console.error("API error fetching applet data:", apiError);
                    response.error = "Could not fetch saved data from the server.";
                }
            }
            break;

          // UPDATED: Added handler for the 'saveData' command from the applet API.
          case 'saveData':
            // This currently sends data to a non-existent endpoint. It allows the
            // applet to function, but data will not persist until the backend is built.
            try {
              // NOTE: The endpoint `/api/applets/${applet.id}/data/` needs to be created on the backend.
              await apiClient.post(`/api/applets/${applet.id}/data/`, payload);
              response.payload = { status: 'ok' };
            } catch (apiError) {
              console.error("API error saving applet data:", apiError);
              response.error = "Could not save data to the server.";
            }
            break;

          default:
            response.error = `Unknown command: ${command}`;
            break;
        }
      } catch (e) {
        response.error = e.message;
      }
      
      // Send the response back to the applet in the iframe
      iframeRef.current.contentWindow.postMessage(response, '*');
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [profile, applet.id]); // Dependency array includes applet.id for API calls

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
    // This creates the basic HTML structure that the applet's JS will run inside of.
    return `
      <!DOCTYPE html>
      <html>
        <head><title>${applet.name}</title></head>
        <body>
          <div id="applet-root"></div>
          <script type="text/javascript">${appletCode}</script>
        </body>
      </html>
    `;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-200">{applet.name}</h2>
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

