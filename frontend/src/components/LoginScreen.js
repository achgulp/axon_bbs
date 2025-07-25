// axon_bbs/frontend/src/components/LoginScreen.js
// ... (rest unchanged)
const handleLogin = async (e) => {
  e.preventDefault();
  setError('');
  try {
    const response = await apiClient.post('/api/token/', {
      username,
      password,
    });
    localStorage.setItem('token', response.data.access);  // Store access token
    onLogin(response.data.access);
  } catch (err) {
    setError('Invalid username or password.');
    console.error(err);
  }
};
