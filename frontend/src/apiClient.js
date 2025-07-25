// axon_bbs/frontend/src/apiClient.js
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
    } else {
      console.warn('No token found in localStorage for request to', config.url);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
