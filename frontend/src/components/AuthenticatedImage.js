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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.


// Full path: axon_bbs/frontend/src/components/AuthenticatedImage.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const AuthenticatedImage = ({ src, alt, className }) => {
  const [imageSrc, setImageSrc] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    // A variable to track if the component is still mounted.
    let isMounted = true; 

    const fetchImage = async () => {
      if (!src) return;

      try {
        // Use the standard apiClient to fetch the image as a binary object (blob)
        const response = await apiClient.get(src, { responseType: 'blob' });
        if (isMounted) {
            // Create a temporary, local URL for the downloaded blob
            const localUrl = URL.createObjectURL(response.data);
            setImageSrc(localUrl);
        }
      } catch (err) {
        console.error("Failed to fetch authenticated image:", err);
        if (isMounted) {
            setError('Could not load image.');
        }
      }
    };

    fetchImage();

    // Cleanup function to run when the component unmounts.
    return () => {
      isMounted = false;
      // Revoke the object URL to free up memory when the component is gone.
      if (imageSrc) {
        URL.revokeObjectURL(imageSrc);
      }
    };
  }, [src]); // Re-run effect if the src prop changes

  if (error) {
    return <div className={className} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#4A5568' }}><span className="text-xs text-red-400">{error}</span></div>;
  }

  if (!imageSrc) {
    // Display a loading spinner or placeholder
    return <div className={className} style={{ backgroundColor: '#4A5568', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-200"></div></div>;
  }

  // Render the standard img tag with the local blob URL
  return <img src={imageSrc} alt={alt} className={className} />;
};

export default AuthenticatedImage;
