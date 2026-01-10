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


// Full path: axon_bbs/frontend/src/components/AuthenticatedVideoPlayer.js
import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const AuthenticatedVideoPlayer = ({ src, type }) => {
  const [videoSrc, setVideoSrc] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    let objectUrl = null;

    const fetchVideo = async () => {
      if (!src) {
        setIsLoading(false);
        return;
      }
      
      setIsLoading(true);
      setError('');

      try {
        const response = await apiClient.get(src, { responseType: 'blob' });
        if (isMounted) {
          const blob = new Blob([response.data], { type });
          objectUrl = URL.createObjectURL(blob);
          setVideoSrc(objectUrl);
        }
      } catch (err) {
        console.error("Failed to fetch authenticated video:", err);
        if (isMounted) {
          setError('Could not load video. Your session may have expired or your identity is locked.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchVideo();

    return () => {
      isMounted = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [src, type]);

  if (isLoading) {
    return <div className="w-full max-w-2xl bg-black aspect-video flex items-center justify-center text-gray-400">Loading video...</div>;
  }

  if (error) {
    return <div className="w-full max-w-2xl bg-black aspect-video flex items-center justify-center text-red-400">{error}</div>;
  }

  return (
    <video controls preload="metadata" className="w-full max-w-2xl rounded bg-black">
      <source src={videoSrc} type={type} />
      Your browser does not support the video tag.
    </video>
  );
};

export default AuthenticatedVideoPlayer;
