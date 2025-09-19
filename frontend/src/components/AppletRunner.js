// Axon BBS - A modern, anonymous, federated bulletin board system.
// Copyright (C) 2025 Achduke7
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY;
// without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.
// If not, see <https://www.gnu.org/licenses/>.


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
    const loadAppletAndProfile = async () => {
      setIsLoading(true);
      setError('');
      try {
        const profilePromise = apiClient.get('/api/user/profile/');
        if (!applet?.code_manifest?.content_hash) {
          throw new Error("Applet has an invalid code manifest.");
        }
        // --- FIX: Use the correct, newly created endpoint ---
        const codeUrl = `/api/content/download/${applet.code_manifest.content_hash}/`;
        const codePromise = apiClient.get(codeUrl);

        const [profileResponse, codeResponse] = await Promise.all([profilePromise, codePromise]);
        
        setProfile(profileResponse.data);
        setAppletCode(codeResponse.data);

      } catch (err) {
        console.error("Failed to load applet prerequisites:", err);
        setError(err.response?.data?.error || err.message || "Could not load applet.");
      } finally {
        setIsLoading(false);
      }
    };
    
    loadAppletAndProfile();
  }, [applet]);

  useEffect(() => {
    const handleMessage = async (event) => {
      // SECURITY: Validate both the origin and the source of the message
      if (event.origin !== window.location.origin) {
        console.warn(`Blocked a postMessage from an unexpected origin: ${event.origin}`);
        return;
      }
      if (event.source !== iframeRef.current?.contentWindow) {
        return;
      }
      const { command, payload, requestId } = event.data;
      let response = { command: `response_${command}`, requestId, payload: null, error: null };

      try {
        if (!profile) { throw new Error("User profile is not available."); }
        switch (command) {
          case 'getUserInfo':
            response.payload = profile;
            break;
          case 'getData':
            const dataResponse = await apiClient.get(`/api/applets/${applet.id}/data/`);
            response.payload = dataResponse.status === 204 ? null : dataResponse.data;
            break;
          case 'saveData':
            const saveResponse = await apiClient.post(`/api/applets/${applet.id}/data/`, payload);
            response.payload = saveResponse.data;
            break;
          case 'getAppletInfo':
            response.payload = applet;
            break;
          case 'postEvent':
            const postResponse = await apiClient.post(`/api/applets/${applet.id}/post_event/`, payload);
            response.payload = postResponse.data;
            break;
          case 'readEvents':
            const readResponse = await apiClient.get(`/api/applets/${applet.id}/read_events/`);
            response.payload = readResponse.data;
            break;
          default:
            return;
        }
      } catch (e) {
        console.error(`Error processing applet command '${command}':`, e);
        response.error = e.response?.data?.error || e.message || 'An unknown error occurred.';
      }
      
      if (iframeRef.current && iframeRef.current.contentWindow) {
        iframeRef.current.contentWindow.postMessage(response, '*');
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [profile, applet]);

  const getIframeContent = () => {
    if (!appletCode) return '';
    const checksum = applet?.code_manifest?.content_hash || 'N/A';
    const debugMode = applet?.is_debug_mode || false;

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
            window.BBS_DEBUG_MODE = ${debugMode};
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
        <h2 className="text-xl font-bold text-gray-200">{applet.name}</h2>
        <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
          ← Back to Applets
        </button>
      </div>
      <div className="w-full h-[75vh] bg-gray-900 border border-gray-700 rounded overflow-hidden">
        {isLoading ? (
          <div className="p-4">Loading applet and user profile...</div>
        ) : error ? (
          <div className="p-4 text-red-500">{error}</div>
        ) : (
          <iframe
            ref={iframeRef}
            title={applet.name}
            srcDoc={getIframeContent()}
            className="w-full h-full"
            sandbox="allow-scripts allow-same-origin"
          />
        )}
      </div>
    </div>
  );
};

export default AppletRunner;
