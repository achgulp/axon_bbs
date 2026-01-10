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


// axon_bbs/frontend/src/components/AnsiViewer.js
import React from 'react';
import Convert from 'ansi-to-html';

const AnsiViewer = ({ content, onClose }) => {
  // Configure the ANSI to HTML converter
  const convert = new Convert({
    fg: '#E2E8F0', // Default text color from your theme
    bg: '#1A202C', // Default background color from your theme
    newline: true, // Use <br/> for newlines
    escapeXML: true,
  });

  // Convert the raw ANSI content to HTML
  const htmlContent = convert.toHtml(content);

  return (
    // A simple modal overlay to display the content
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      zIndex: 1000,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    }} onClick={onClose}>
      <div
        style={{
          backgroundColor: '#1A202C',
          color: '#E2E8F0',
          fontFamily: 'monospace',
          padding: '20px',
          borderRadius: '8px',
          maxWidth: '90%',
          maxHeight: '90%',
          overflow: 'auto',
          border: '1px solid #4A5568'
        }}
        // Prevent clicks inside the viewer from closing it
        onClick={(e) => e.stopPropagation()}
      >
        <pre dangerouslySetInnerHTML={{ __html: htmlContent }} />
      </div>
    </div>
  );
};

export default AnsiViewer;

