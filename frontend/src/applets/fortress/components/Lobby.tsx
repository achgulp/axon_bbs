
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { GameEvent, GameEventType, Player, UserInfo } from '../types';
import { gameService } from '../services/gameService';
import { PLAYER_COLORS, AI_USER_INFO } from '../constants';
import { soundService } from '../services/soundService';

interface LobbyProps {
  onStartGame: (self: Player, opponent: UserInfo) => void;
  userInfo: UserInfo;
}

const Lobby: React.FC<LobbyProps> = ({ onStartGame, userInfo }) => {
  const [status, setStatus] = useState('Looking for a game...');
  const [waiting, setWaiting] = useState(false);
  const [countdown, setCountdown] = useState<number>(30);
  const pollingId = useRef<number | null>(null);
  const aiTimeoutId = useRef<number | null>(null);
  const countdownIntervalId = useRef<number | null>(null);

  const cleanupTimers = useCallback(() => {
    if (aiTimeoutId.current) {
      clearTimeout(aiTimeoutId.current);
      aiTimeoutId.current = null;
    }
    if (countdownIntervalId.current) {
      clearInterval(countdownIntervalId.current);
      countdownIntervalId.current = null;
    }
  }, []);

  const handleGameEvent = useCallback((event: GameEvent) => {
    if (event.sender.pubkey === userInfo.pubkey) return;

    if (event.type === GameEventType.JoinGame && !waiting) {
      cleanupTimers();
      setStatus(`Game found with ${event.sender.nickname}. Starting...`);
      const self: Player = { ...userInfo, id: 1, color: PLAYER_COLORS[1] };
      
      gameService.postEvent({
        type: GameEventType.StartGame,
        payload: { opponent: self },
      }, userInfo);

      soundService.playSound('click');
      onStartGame(self, event.sender);

    } else if (event.type === GameEventType.StartGame && waiting) {
        if (event.payload.opponent.pubkey === userInfo.pubkey) {
            cleanupTimers();
            setStatus(`Game started by ${event.sender.nickname}!`);
            const self: Player = { ...userInfo, id: 0, color: PLAYER_COLORS[0] };
            soundService.playSound('click');
            onStartGame(self, event.sender);
        }
    }
  }, [onStartGame, userInfo, waiting, cleanupTimers]);

  useEffect(() => {
    pollingId.current = gameService.startPolling(handleGameEvent);

    return () => {
      if (pollingId.current) gameService.stopPolling(pollingId.current);
      cleanupTimers();
    };
  }, [handleGameEvent, cleanupTimers]);

  const joinGame = () => {
    setStatus('Waiting for another player...');
    setWaiting(true);
    setCountdown(30);
    gameService.postEvent({ type: GameEventType.JoinGame, payload: {} }, userInfo);
    soundService.playSound('click');

    // AI game timeout
    aiTimeoutId.current = window.setTimeout(() => {
        cleanupTimers();
        setStatus('No players found. Starting game against AI.');
        const self: Player = { ...userInfo, id: 0, color: PLAYER_COLORS[0] };
        onStartGame(self, AI_USER_INFO);
    }, 30000);

    // Countdown UI timer
    countdownIntervalId.current = window.setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          if (countdownIntervalId.current) clearInterval(countdownIntervalId.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-900 text-white p-4">
      <div className="text-center bg-gray-800 p-10 rounded-xl shadow-2xl border border-blue-500/30">
        <h1 className="text-5xl font-bold mb-4 text-blue-400">Fortress Overlord</h1>
        <p className="text-xl text-gray-300 mb-8">
          {status}
          {waiting && <span className="font-mono text-2xl block mt-4">{countdown}</span>}
        </p>
        {!waiting && (
          <button
            onClick={joinGame}
            className="px-10 py-4 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg text-2xl transition-transform transform hover:scale-105"
          >
            Find Game
          </button>
        )}
      </div>
       <div className="absolute bottom-4 text-sm text-gray-500">
         Note: This is a 2-player game. Open this applet in another tab or have another user join to start a match. If no opponent is found in 30 seconds, you will play against an AI.
       </div>
    </div>
  );
};

export default Lobby;
