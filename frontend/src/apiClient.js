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

// UPDATED: The response interceptor is now smarter about 401 errors.
apiClient.interceptors.response.use(
  (response) => response, 
  (error) => {
    if (error.response && error.response.status === 401) {
      // Don't intercept for the token endpoint, to allow for failed login attempts
      if (error.config.url.includes('/api/token/')) {
        return Promise.reject(error);
      }

      // NEW: Check for the specific 'identity_locked' error.
      // If this error occurs, we DON'T want to log out. We let the
      // component that made the request handle it by showing the unlock form.
      if (error.response.data && error.response.data.error === 'identity_locked') {
        return Promise.reject(error);
      }

      // For all other 401 errors, we assume the session is invalid and log out.
      console.warn("Session expired or token is invalid. Logging out.");
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
