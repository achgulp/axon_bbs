// axon_bbs/frontend/src/components/LoginScreen.js
const handleLogin = async (e) => {
  e.preventDefault();
  setError('');
  try {
    const response = await apiClient.post('/api/token/', { username, password });
    localStorage.setItem('token', response.data.access); // Ensure 'access' matches your token field
    onLogin(response.data.access);
  } catch (err) {
    setError('Invalid username or password.');
    console.error(err);
  }
};
