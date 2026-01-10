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


// Full path: axon_bbs/frontend/src/applet_api/api.js
// UPDATED: Added new functions for agent/event-bus interaction.
window.bbs = {
  _callbacks: {},
  _requestId: 0,

  _handleMessage: function(event) {
    const { command, payload, requestId, error } = event.data;
    if (command && command.startsWith('response_') && this._callbacks[requestId]) {
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
      // Target window.parent, specifying the exact origin for security
      window.parent.postMessage({ command, payload, requestId }, window.location.origin);
    });
  },

  // --- Standard API ---
  getUserInfo: function() {
    return this._postMessage('getUserInfo');
  },

  getData: function() {
    return this._postMessage('getData');
  },

  saveData: function(newData) {
    return this._postMessage('saveData', newData);
  },

  // --- NEW: Event Bus API ---
  getAppletInfo: function() {
    return this._postMessage('getAppletInfo');
  },

  postEvent: function(eventData) {
    return this._postMessage('postEvent', eventData);
  },

  readEvents: function() {
    return this._postMessage('readEvents');
  }
};

window.addEventListener('message', (event) => window.bbs._handleMessage(event));
