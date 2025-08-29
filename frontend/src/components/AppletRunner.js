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
    const handleMessage = (event) => {
      if (event.source !== iframeRef.current?.contentWindow) {
        return;
      }
      const { command } = event.data;
      if (command === 'getUserInfo') {
        iframeRef.current.contentWindow.postMessage({
          command: 'userInfo',
          payload: profile,
        }, '*');
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [profile]);

  useEffect(() => {
    if (!applet || !applet.code_manifest || !applet.code_manifest.content_hash) {
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
        if (err.response && err.response.data.error === 'identity_locked') {
          setError("Your identity is locked. Please unlock it to run applets.");
        } else {
          setError("Could not download applet code. It may still be syncing.");
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [applet]);

  const getIframeContent = () => {
    if (!appletCode) return '';
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${applet.name}</title>
          <style>
            body { margin: 0; padding: 0; background-color: #1a202c; color: #e2e8f0; font-family: sans-serif; }
          </style>
        </head>
        <body>
          <div id="applet-root"></div>
          <script>${appletCode}</script>
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
