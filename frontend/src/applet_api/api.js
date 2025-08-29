// Full path: axon_bbs/frontend/src/applet_api/api.js

// This file provides a simple API for sandboxed applets to communicate with the main BBS application.
// Applet developers can use this to access BBS functionality securely.

window.bbs = {
  // Store callbacks for API responses
  _callbacks: {},

  // Internal function to handle incoming messages from the host
  _handleMessage: function(event) {
    const { command, payload } = event.data;
    if (this._callbacks[command]) {
      this._callbacks[command](payload);
      delete this._callbacks[command]; // Use callback only once
    }
  },

  /**
   * Fetches information about the current user.
   * @returns {Promise<object>} A promise that resolves with the user's profile object 
   * (e.g., { username, nickname, pubkey }).
   */
  getUserInfo: function() {
    return new Promise((resolve) => {
      // Register a callback to handle the response
      this._callbacks['userInfo'] = resolve;
      // Send the request to the host application
      window.parent.postMessage({ command: 'getUserInfo' }, '*');
    });
  },

  /**
   * (To be implemented)
   * Fetches the applet's shared data from BitSync.
   * @returns {Promise<object>} A promise that resolves with the shared data object.
   */
  getData: function() {
    console.log("bbs.getData() is not yet implemented.");
    return Promise.resolve({});
  },

  /**
   * (To be implemented)
   * Saves new shared data to BitSync.
   * @param {object} newData - The JSON-serializable object to save.
   * @returns {Promise<void>} A promise that resolves when the save is complete.
   */
  saveData: function(newData) {
    console.log("bbs.saveData() is not yet implemented.", newData);
    return Promise.resolve();
  }
};

// Listen for messages from the host window
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
