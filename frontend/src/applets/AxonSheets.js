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


// Full path: axon_bbs/frontend/src/applets/AxonSheets.js

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
      // --- FIX START ---
      // Reverted targetOrigin to '*' which is necessary for srcDoc iframes.
      // Security is handled by the parent window verifying the message origin.
      window.parent.postMessage({ command, payload, requestId }, '*');
      // --- FIX END ---
    });
  },
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    // --- SETUP: Wrap entire execution in a try...catch for better error reporting ---
    try {
        // 1. SETUP: Define styles, create HTML structure, and declare variables.
        const styles = `
            :root {
                --bg-dark: #1a202c; --bg-medium: #2d3748; --bg-light: #4a5568;
                --border-color: #718096; --text-primary: #e2e8f0; --accent-blue: #4299e1;
                --header-bg: #2c3342; --selected-bg: #1c4a78; --selected-border: #63b3ed;
            }
            body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: Arial, sans-serif; }
            .app-container { display: flex; flex-direction: column; height: 100vh; background-color: var(--bg-dark); color: var(--text-primary); }
            .toolbar { padding: 8px; background-color: var(--bg-medium); display: flex; align-items: center; border-bottom: 1px solid var(--border-color); }
            .cell-name-box { width: 80px; text-align: center; padding: 5px; background-color: var(--bg-dark); border: 1px solid var(--border-color); border-radius: 4px; margin-right: 8px; }
            .formula-bar { flex-grow: 1; padding: 5px; background-color: var(--bg-dark); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-family: monospace; }
            .grid-container { flex-grow: 1; overflow: auto; }
            .grid-table { border-collapse: collapse; table-layout: fixed; }
            .grid-table th, .grid-table td { border: 1px solid var(--border-color); min-width: 80px; height: 25px; box-sizing: border-box; padding: 2px 4px; }
            .grid-table th { background-color: var(--header-bg); text-align: center; font-weight: bold; user-select: none; }
            .grid-table th.row-header { min-width: 50px; }
            .grid-table td { background-color: var(--bg-medium); cursor: cell; text-align: left; white-space: nowrap; overflow: hidden; }
            .grid-table td.selected { background-color: var(--selected-bg); outline: 2px solid var(--selected-border); outline-offset: -2px; }
            .grid-table td[data-type="number"] { text-align: right; }
            #status-bar { padding: 4px 8px; background-color: var(--bg-medium); border-top: 1px solid var(--border-color); font-size: 0.8em; text-align: right; color: #a0aec0; }
            #debug-dialog { display: none; position: absolute; bottom: 30px; left: 10px; width: 300px; height: 200px; background-color: rgba(0,0,0,0.7); border: 1px solid #4a5568; border-radius: 5px; color: #9AE6B4; font-family: monospace; font-size: 12px; overflow-y: scroll; padding: 5px; z-index: 1000; }
        `;
        const styleSheet = document.createElement("style");
        styleSheet.innerText = styles;
        document.head.appendChild(styleSheet);
        
        document.getElementById('applet-root').innerHTML = `
            <div class="app-container">
                <div class="toolbar">
                    <div id="cell-name-box" class="cell-name-box">A1</div>
                    <input type="text" id="formula-bar" class="formula-bar" />
                </div>
                <div id="grid-container" class="grid-container"></div>
                <div id="status-bar">Ready</div>
                <div id="debug-dialog"></div>
            </div>
        `;

        // --- VARIABLES & DOM REFERENCES ---
        const COLS = 26; // A-Z
        const ROWS = 100;
        const gridContainer = document.getElementById('grid-container');
        const formulaBar = document.getElementById('formula-bar');
        const cellNameBox = document.getElementById('cell-name-box');
        const statusBar = document.getElementById('status-bar');
        const debugDialog = document.getElementById('debug-dialog');
        
        let sheetData = {};
        let selectedCell = { col: 0, row: 0 };
        let saveTimeout = null;

        // --- FUNCTIONS ---
        function debugLog(message) {
            if (window.BBS_DEBUG_MODE !== true) return;
            debugDialog.style.display = 'block';
            const logEntry = document.createElement('div');
            logEntry.textContent = `> ${message}`;
            debugDialog.appendChild(logEntry);
            debugDialog.scrollTop = debugDialog.scrollHeight;
        }

        function getCellAddress(col, row) {
            return `${String.fromCharCode(65 + col)}${row + 1}`;
        }

        function parseCellAddress(address) {
            const match = address.match(/^([A-Z])([0-9]+)$/i);
            if (!match) return null;
            return { col: match[1].toUpperCase().charCodeAt(0) - 65, row: parseInt(match[2], 10) - 1 };
        }

        function renderGrid() {
            debugLog("Checkpoint: renderGrid() started.");
            let tableHTML = '<table class="grid-table"><thead><tr><th class="row-header"></th>';
            for (let col = 0; col < COLS; col++) {
                tableHTML += `<th>${String.fromCharCode(65 + col)}</th>`;
            }
            tableHTML += '</tr></thead><tbody>';
            for (let row = 0; row < ROWS; row++) {
                tableHTML += `<tr><th class="row-header">${row + 1}</th>`;
                for (let col = 0; col < COLS; col++) {
                    const address = getCellAddress(col, row);
                    tableHTML += `<td id="cell-${address}"></td>`;
                }
                tableHTML += '</tr>';
            }
            tableHTML += '</tbody></table>';
            gridContainer.innerHTML = tableHTML;
            recalculateAndDrawSheet();
            debugLog("Checkpoint: renderGrid() finished.");
        }

        function selectCell(col, row) {
            const prevAddress = getCellAddress(selectedCell.col, selectedCell.row);
            const prevCellEl = document.getElementById(`cell-${prevAddress}`);
            if (prevCellEl) prevCellEl.classList.remove('selected');

            selectedCell = { col, row };
            const newAddress = getCellAddress(col, row);
            const newCellEl = document.getElementById(`cell-${newAddress}`);
            if (newCellEl) {
                newCellEl.classList.add('selected');
                newCellEl.focus();
            }
            
            cellNameBox.textContent = newAddress;
            formulaBar.value = sheetData[newAddress]?.value || '';
        }

        function recalculateAndDrawSheet() {
            const evaluatedValues = {};
            
            for (let row = 0; row < ROWS; row++) {
                for (let col = 0; col < COLS; col++) {
                    const address = getCellAddress(col, row);
                    const displayValue = evaluateCell(address, evaluatedValues);
                    const cellEl = document.getElementById(`cell-${address}`);
                    if (cellEl) {
                        cellEl.textContent = displayValue;
                        if (typeof displayValue === 'number') {
                            cellEl.dataset.type = 'number';
                        } else {
                            cellEl.dataset.type = 'string';
                        }
                    }
                }
            }
        }
        
        function evaluateCell(address, evaluatedValues, visiting = new Set()) {
            if (address in evaluatedValues) return evaluatedValues[address];
            if (visiting.has(address)) return '#CIRC!';
            
            const cellData = sheetData[address];
            if (!cellData || !cellData.value) return '';

            let rawValue = cellData.value;
            if (typeof rawValue !== 'string' || !rawValue.startsWith('=')) {
                evaluatedValues[address] = rawValue;
                return rawValue;
            }

            visiting.add(address);
            
            let result;
            const formula = rawValue.substring(1);
            
            const sumMatch = formula.toUpperCase().match(/^SUM\(([A-Z][0-9]+):([A-Z][0-9]+)\)$/);
            if (sumMatch) {
                const start = parseCellAddress(sumMatch[1]);
                const end = parseCellAddress(sumMatch[2]);
                let sum = 0;
                if (start && end) {
                    for (let r = start.row; r <= end.row; r++) {
                        for (let c = start.col; c <= end.col; c++) {
                            const cellAddr = getCellAddress(c, r);
                            const val = parseFloat(evaluateCell(cellAddr, evaluatedValues, new Set(visiting)));
                            if (!isNaN(val)) sum += val;
                        }
                    }
                }
                result = sum;
            } else {
                try {
                    let sanitizedFormula = formula.replace(/[A-Z][0-9]+/gi, (match) => {
                        const val = evaluateCell(match.toUpperCase(), evaluatedValues, new Set(visiting));
                        const num = parseFloat(val);
                        return isNaN(num) ? '0' : num;
                    });
                    
                    if (/^[0-9+\-*/().\s]+$/.test(sanitizedFormula)) {
                        result = new Function(`return ${sanitizedFormula}`)();
                    } else {
                        result = '#NAME?';
                    }
                } catch (e) {
                    result = '#ERROR!';
                }
            }

            visiting.delete(address);
            evaluatedValues[address] = result;
            return result;
        }

        function handleInput(value) {
            const address = getCellAddress(selectedCell.col, selectedCell.row);
            if (!value) {
                delete sheetData[address];
            } else {
                sheetData[address] = { value };
            }
            recalculateAndDrawSheet();
            scheduleSave();
        }
        
        function scheduleSave() {
            statusBar.textContent = 'Saving...';
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(async () => {
                try {
                    await bbs.saveData({ cells: sheetData });
                    statusBar.textContent = 'All changes saved.';
                    debugLog('Data saved successfully.');
                } catch (e) {
                    statusBar.textContent = 'Save failed!';
                    debugLog(`Error saving data: ${e.message}`);
                }
            }, 1500);
        }

        // --- 2. RUNTIME: Initialize the applet. ---
        debugLog("AxonSheets Applet initializing...");

        renderGrid();
        debugLog("Checkpoint: Grid rendered.");

        selectCell(0, 0);
        debugLog("Checkpoint: Initial cell selected.");

        const [userInfo, savedData] = await Promise.all([bbs.getUserInfo(), bbs.getData()]);
        debugLog("Checkpoint: User and saved data fetched.");
        
        if (userInfo) {
            statusBar.textContent = `Welcome, ${userInfo.nickname || userInfo.username}!`;
        }
        if (savedData && savedData.cells) {
            sheetData = savedData.cells;
            recalculateAndDrawSheet();
            debugLog("Loaded saved sheet data.");
        } else {
            debugLog("No saved data found. Starting with a blank sheet.");
        }

        // Add event listeners
        formulaBar.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleInput(formulaBar.value);
                const nextRow = Math.min(ROWS - 1, selectedCell.row + 1);
                selectCell(selectedCell.col, nextRow);
            }
        });

        gridContainer.addEventListener('click', (e) => {
            if (e.target.tagName === 'TD') {
                const address = e.target.id.replace('cell-', '');
                const coords = parseCellAddress(address);
                if (coords) selectCell(coords.col, coords.row);
            }
        });

        gridContainer.addEventListener('dblclick', (e) => {
            if (e.target.tagName === 'TD') {
                formulaBar.focus();
            }
        });

        window.addEventListener('keydown', (e) => {
            let { col, row } = selectedCell;
            let moved = false;
            switch (e.key) {
                case 'ArrowUp': row = Math.max(0, row - 1); moved = true; break;
                case 'ArrowDown': row = Math.min(ROWS - 1, row + 1); moved = true; break;
                case 'ArrowLeft': col = Math.max(0, col - 1); moved = true; break;
                case 'ArrowRight': col = Math.min(COLS - 1, col + 1); moved = true; break;
                default:
                    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && document.activeElement !== formulaBar) {
                        formulaBar.focus();
                    }
                    break;
            }
            if (moved) {
                e.preventDefault();
                selectCell(col, row);
            }
        });
        debugLog("Checkpoint: Event listeners attached.");
        
    } catch (e) {
        const root = document.getElementById('applet-root');
        root.innerHTML = `<p style="color: red;">Error initializing AxonSheets: ${e.message}</p><pre>${e.stack}</pre>`;
        console.error("Applet initialization failed:", e);
        // Also log to our debug console if it exists
        const debugDialog = document.getElementById('debug-dialog');
        if (debugDialog) {
            debugDialog.style.display = 'block';
            debugDialog.innerHTML += `<div>FATAL ERROR: ${e.message}</div>`;
        }
    }
})();


