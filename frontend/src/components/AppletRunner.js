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


// Full path: axon_bbs/frontend/src/components/AppletRunner.js
import React, { useState, useEffect, useRef } from 'react';
import apiClient from '../apiClient';

// --- Helper function for SHA-256 Hashing ---
async function sha256(message) {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
}

const LoadingAnimation = ({ status }) => {
    return (
        <div style={{
            width: '100%',
            height: '100%',
            backgroundColor: '#0a0a1a',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            position: 'relative',
            fontFamily: 'monospace',
            color: '#00ffcc',
        }}>
            <style>{`
                @keyframes stars-twinkle {
                    0% { opacity: 0.2; }
                    50% { opacity: 0.8; }
                    100% { opacity: 0.2; }
                }
                @keyframes ship-land {
                    0% { transform: translateY(-150px); }
                    100% { transform: translateY(0); }
                }
                @keyframes ramp-deploy {
                    0% { transform: scaleY(0); transform-origin: top; }
                    100% { transform: scaleY(1); transform-origin: top; }
                }
                @keyframes spaceman-walk {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(50px); }
                }
                @keyframes flag-plant {
                    0% { transform: translateY(20px); opacity: 0; }
                    100% { transform: translateY(0); opacity: 1; }
                }
                .star {
                    position: absolute;
                    background: white;
                    border-radius: 50%;
                    animation: stars-twinkle 3s infinite;
                }
            `}</style>
            {[...Array(50)].map((_, i) => {
                const size = Math.random() * 2 + 1;
                return (
                    <div key={i} className="star" style={{
                        width: `${size}px`,
                        height: `${size}px`,
                        top: `${Math.random() * 100}%`,
                        left: `${Math.random() * 100}%`,
                        animationDelay: `${Math.random() * 3}s`,
                    }}></div>
                );
            })}
            <svg width="300" height="300" viewBox="0 0 300 300">
                {/* Planet Surface */}
                <path d="M0 300 C 50 250, 250 250, 300 300 L 300 300 L 0 300 Z" fill="#4a2a0a" />
                <circle cx="50" cy="280" r="15" fill="#3a1a00" />
                <circle cx="220" cy="290" r="25" fill="#3a1a00" />

                {/* Spaceship */}
                <g style={{ animation: 'ship-land 2s ease-out forwards' }}>
                    <path d="M150 100 L120 180 L180 180 Z" fill="#c0c0c0" />
                    <rect x="110" y="180" width="80" height="10" fill="#a0a0a0" />
                    <circle cx="150" cy="130" r="10" fill="#00ffff" />
                    {/* Ramp */}
                    <path d="M140 170 L130 260 L170 260 L160 170 Z" fill="#808080" style={{ animation: 'ramp-deploy 2s 2s ease-in forwards' }}/>
                </g>
                
                {/* Spaceman */}
                <g style={{ animation: 'spaceman-walk 2s 4s ease-in-out forwards' }}>
                    <circle cx="145" cy="160" r="8" fill="white" /> {/* Helmet */}
                    <rect x="142" y="168" width="6" height="15" fill="#e0e0e0" /> {/* Body */}
                </g>

                {/* Flag */}
                 <g style={{ animation: 'flag-plant 1s 6s ease-out forwards', opacity: 0 }}>
                    <rect x="200" y="240" width="3" height="30" fill="#a0a0a0" />
                    <rect x="203" y="240" width="25" height="15" fill="#ff4136" />
                </g>
            </svg>
            <div style={{
                marginTop: '20px',
                fontSize: '1.2em',
                textShadow: '0 0 5px #00ffcc',
            }}>
                {status}
            </div>
        </div>
    );
};

const AppletRunner = ({ applet, onBack, attachmentContext = null }) => {
  const [appletCode, setAppletCode] = useState(null);
  const [libraryScripts, setLibraryScripts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingStatus, setLoadingStatus] = useState('Initializing...');
  const [error, setError] = useState('');
  const [profile, setProfile] = useState(null);
  const iframeRef = useRef(null);

  useEffect(() => {
    const loadAppletAndProfile = async () => {
      setIsLoading(true);
      setError('');
      try {
        setLoadingStatus('Fetching user profile...');
        const profilePromise = apiClient.get('/api/user/profile/');

        if (!applet?.code_manifest?.content_hash) {
          throw new Error("Applet has an invalid code manifest.");
        }
        
        // --- Load Shared Libraries ---
        if (applet.parameters?.required_libraries) {
            setLoadingStatus('Loading shared libraries...');
            const libraryPromises = applet.parameters.required_libraries.map(libName =>
                apiClient.get(`/api/libraries/${libName}/`, { responseType: 'text' })
            );
            const libraryResponses = await Promise.all(libraryPromises);
            setLibraryScripts(libraryResponses.map(res => res.data));
            setLoadingStatus('Libraries loaded.');
        }

        setLoadingStatus('Downloading applet package...');
        const codeUrl = `/api/content/stream/${applet.code_manifest.content_hash}/?for_verification`;
        const codePromise = apiClient.get(codeUrl, { 
            timeout: 60000,
            responseType: 'text' 
        });

        const [profileResponse, codeResponse] = await Promise.all([profilePromise, codePromise]);
        
        setProfile(profileResponse.data);
        const receivedPayloadString = codeResponse.data;

        setLoadingStatus('Verifying package integrity...');
        const calculatedHash = await sha256(receivedPayloadString);
        
        if (calculatedHash !== applet.code_manifest.content_hash) {
            console.error(`CRITICAL: Checksum mismatch! Expected ${applet.code_manifest.content_hash}, but calculated ${calculatedHash}`);
            throw new Error(`Code integrity check failed. The downloaded applet code may be corrupted or tampered with. Please try again.`);
        }
        setLoadingStatus('Verification successful. Unpacking applet...');

        const payload = JSON.parse(receivedPayloadString);
        let finalAppletCode;

        if (payload.type === 'file' && payload.data) {
            finalAppletCode = atob(payload.data);
        } else if (payload.type === 'applet_code' && payload.code) {
            finalAppletCode = payload.code;
        } else {
            throw new Error("Invalid or unrecognized applet package format.");
        }

        setTimeout(() => {
            setAppletCode(finalAppletCode);
            setIsLoading(false);
        }, 1000);

      } catch (err) {
        console.error("Failed to load applet prerequisites:", err);
        setError(err.response?.data?.error || err.message || "Could not load applet.");
        setIsLoading(false);
      }
    };
    
    loadAppletAndProfile();
  }, [applet]);

  useEffect(() => {
    const handleMessage = async (event) => {
      if (event.origin !== window.location.origin || event.source !== iframeRef.current?.contentWindow) return;

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
          case 'getAttachmentContext':
            response.payload = attachmentContext;
            break;
          case 'getAttachmentBlob':
            const hash = payload?.hash || attachmentContext?.content_hash;
            if (!hash) {
                throw new Error("No attachment context or hash is available to fetch.");
            }
            const blob = await apiClient.getBlob(`/api/content/stream/${hash}/`);
            response.payload = blob;
            break;
          case 'postEvent':
            const postResponse = await apiClient.post(`/api/applets/${applet.id}/post_event/`, payload);
            response.payload = postResponse.data;
            break;
          case 'readEvents':
            // Detect browser timezone and pass to backend for timestamp conversion
            const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const readResponse = await apiClient.get(`/api/applets/${applet.id}/read_events/`, {
              params: { tz: userTimezone }
            });
            response.payload = readResponse.data;
            break;
          case 'fetch':
            const { url, options = {} } = payload;
            if (!url) {
              throw new Error("fetch command requires a URL");
            }
            // Perform the fetch request using apiClient
            const method = options.method || 'GET';
            const headers = options.headers || {};
            const body = options.body;

            let fetchResponse;
            if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
              fetchResponse = await apiClient({
                method: method,
                url: url,
                headers: headers,
                data: body ? (typeof body === 'string' ? JSON.parse(body) : body) : undefined
              });
            } else {
              fetchResponse = await apiClient({
                method: method,
                url: url,
                headers: headers
              });
            }
            response.payload = fetchResponse.data;
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
  }, [profile, applet, attachmentContext]);

  const getIframeContent = () => {
    if (!appletCode) return '';
    const checksum = applet?.code_manifest?.content_hash || 'N/A';
    const debugMode = applet?.is_debug_mode || false;

    // Create blob URLs for libraries to avoid embedding issues
    const libraryBlobUrls = libraryScripts.map((scriptContent, index) => {
        console.log(`Creating blob for library ${index + 1}/${libraryScripts.length}, length: ${scriptContent.length}`);
        const blob = new Blob([scriptContent], { type: 'application/javascript' });
        return URL.createObjectURL(blob);
    });

    // Create blob URL for applet code
    const appletBlob = new Blob([appletCode], { type: 'application/javascript' });
    const appletBlobUrl = URL.createObjectURL(appletBlob);

    // Generate script tags that reference the blob URLs
    const libraryScriptTags = libraryBlobUrls.map(url =>
        `<script src="${url}"></script>`
    ).join('\n    ');

    const html =
      '<!DOCTYPE html>\n' +
      '<html>\n' +
      '  <head>\n' +
      '    <title>' + applet.name + '</title>\n' +
      '    ' + libraryScriptTags + '\n' +
      '  </head>\n' +
      '  <body>\n' +
      '    <div id="applet-root"></div>\n' +
      '    <script>\n' +
      '      window.BBS_APPLET_CHECKSUM = \'' + checksum + '\';\n' +
      '      window.BBS_DEBUG_MODE = ' + debugMode + ';\n' +
      '    </script>\n' +
      '    <script src="' + appletBlobUrl + '"></script>\n' +
      '  </body>\n' +
      '</html>';

    return html;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-200">{applet.name}</h2>
        {onBack && 
            <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded">
                ← Back
            </button>
        }
      </div>
      <div className="w-full h-[75vh] bg-gray-900 border border-gray-700 rounded overflow-hidden">
        {isLoading ? (
          <LoadingAnimation status={loadingStatus} />
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
