// Full path: axon_bbs/frontend/src/applet_api/api.js
window.bbs = {
  _callbacks: {},
  _requestId: 0,

  _handleMessage: function(event) {
    const { command, payload, requestId, error } = event.data;
    if (command.startsWith('response_') && this._callbacks[requestId]) {
      const { resolve, reject } = this._callbacks[requestId];
      if (error) {
        reject(new Error(error));
      } else {
        resolve(payload);
      }
      delete this._callbacks[requestId];
    }
  },

  _postMessage: function(command, payload = {}) {
    return new Promise((resolve, reject) => {
      const requestId = this._requestId++;
      this._callbacks[requestId] = { resolve, reject };
      window.parent.postMessage({ command, payload, requestId }, '*');
    });
  },

  getUserInfo: function() {
    return this._postMessage('getUserInfo');
  },

  getData: function() {
    return this._postMessage('getData');
  },

  saveData: function(newData) {
    return this._postMessage('saveData', newData);
  }
};

window.addEventListener('message', (event) => window.bbs._handleMessage(event));
