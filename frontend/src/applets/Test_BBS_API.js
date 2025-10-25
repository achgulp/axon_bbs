// --- Start of Applet API Helper (MANDATORY) ---
window.bbs = {
  _callbacks: {},
  _requestId: 0,
  _handleMessage: function(event) {
    const { command, payload, requestId, error } = event.data;
    if (command && command.startsWith('response_') && this._callbacks[requestId]) {
      const { resolve, reject } = this._callbacks[requestId];
      if (error) { reject(new Error(error)); } else { resolve(payload); }
      delete this._callbacks[requestId];
    }
  },
  _postMessage: function(command, payload = {}) {
    return new Promise((resolve, reject) => {
      const requestId = this._requestId++;
      this._callbacks[requestId] = { resolve, reject };
      if (window.parent !== window) {
        window.parent.postMessage({ command, payload, requestId }, '*');
      } else {
        console.warn("BBS API: Not running in a frame.");
        if (command === 'getUserInfo') {
          resolve({ username: 'test', nickname: 'Test User', pubkey: 'test123' });
        } else if (command === 'getAppletInfo') {
          resolve({ id: 'test', name: 'Test', parameters: {} });
        } else {
          resolve({});
        }
      }
    });
  },
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); },
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---

// --- Main Execution ---
(async function() {
  try {
    console.log('=== BBS API Test Starting ===');

    // Get user info
    const userInfo = await window.bbs.getUserInfo();
    console.log('User Info:', userInfo);

    // Get applet info
    const appletInfo = await window.bbs.getAppletInfo();
    console.log('Applet Info:', appletInfo);

    // Display on page
    const container = document.getElementById('applet-root');
    container.innerHTML = `
      <div style="padding: 20px; font-family: monospace;">
        <h1>BBS API Test</h1>
        <p>Hello from ${userInfo.nickname}!</p>
        <p>Your pubkey: ${userInfo.pubkey}</p>
        <p>Applet ID: ${appletInfo.id}</p>
        <p style="color: green; font-weight: bold;">✓ BBS API is working!</p>
      </div>
    `;

    console.log('=== BBS API Test Complete ===');

  } catch (error) {
    console.error('BBS API Test Error:', error);
    document.getElementById('applet-root').innerHTML = `
      <div style="padding: 20px; color: red;">
        <h1>Error</h1>
        <p>${error.message}</p>
      </div>
    `;
  }
})();
