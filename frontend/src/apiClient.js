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


// Full path: axon_bbs/frontend/src/apiClient.js
import axios from 'axios';

const apiClient = axios.create({
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, 
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response, 
  (error) => {
    if (error.response && error.response.status === 401) {
      if (error.config.url.includes('/api/token/')) {
        return Promise.reject(error);
      }
      if (error.response.data && error.response.data.error === 'identity_locked') {
        return Promise.reject(error);
      }
      console.warn("Session expired or token is invalid. Logging out.");
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    
    return Promise.reject(error);
  }
);

// Specialized function to fetch binary data like videos or images
apiClient.getBlob = async (url) => {
    const token = localStorage.getItem('token');
    const response = await fetch(url, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!response.ok) {
        if (response.status === 401) {
            // Attempt to parse the JSON error body for identity_locked
            try {
                const errorData = await response.json();
                if (errorData.error === 'identity_locked') {
                    // Re-throw a specific error type that components can catch
                    const err = new Error('identity_locked');
                    err.response = { data: errorData };
                    throw err;
                }
            } catch (e) {
                // --- FIX START ---
                // This block is intentionally empty. If the 401 response isn't
                // valid JSON (e.g., just plain text), we can't parse a specific
                // error message, so we fall through to the generic error below.
                // This comment satisfies strict linting rules.
                // --- FIX END ---
            }
        }
        throw new Error(`Failed to fetch blob with status: ${response.status}`);
    }
    return response.blob();
};

export default apiClient;
