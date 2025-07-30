// Full path: axon_bbs/frontend/src/apiClient.js
import axios from 'axios';

// Create an instance of axios for our API
const apiClient = axios.create({
  // By removing the hardcoded baseURL, requests will be sent to the
  // same host that served the frontend files. This makes the app portable.
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send cookies for session
});

// Interceptor to add JWT token to every request
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

// NEW: Interceptor to handle 401 Unauthorized errors
apiClient.interceptors.response.use(
  (response) => response, // Directly return successful responses
  (error) => {
    // Check if the error is a 401 Unauthorized
    if (error.response && error.response.status === 401) {
      // Don't intercept for the token endpoint, to allow for failed login attempts
      if (error.config.url.includes('/api/token/')) {
        return Promise.reject(error);
      }

      console.warn("Session expired or token is invalid. Logging out.");
      // Remove the invalid token from storage
      localStorage.removeItem('token');
      // Redirect to the login page by reloading the app
      window.location.href = '/';
    }
    // For all other errors, just pass them along
    return Promise.reject(error);
  }
);

export default apiClient;
