
import React, { useState, useEffect, useCallback } from 'react';
import * as Tone from 'tone';
import Game from './components/Game';
import Lobby from './components/Lobby';
import { GameState, Player, UserInfo } from './types';
import { soundService } from './services/soundService';

const App: React.FC = () => {
  const [gameState, setGameState] = useState<GameState>(GameState.Lobby);
  const [isAudioStarted, setIsAudioStarted] = useState<boolean>(false);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [player, setPlayer] = useState<Player | null>(null);
  const [opponent, setOpponent] = useState<UserInfo | null>(null);

  useEffect(() => {
    // Mock the window.bbs API for local development if it doesn't exist.
    // In the Axon BBS environment, this will be provided.
    if (!window.bbs) {
      console.warn("BBS API not found, using mock for local development.");
      window.bbs = {
        _callbacks: {},
        _requestId: 0,
        _handleMessage: function(event) {}, // Simplified for mock
        _postMessage: function(command, payload = {}) {
            return new Promise((resolve, reject) => {
                console.log(`Mock BBS Call: ${command}`, payload);
                if (command === 'getUserInfo') {
                    resolve({ username: 'local_user', nickname: 'Player 1', pubkey: 'local_pubkey_12345' });
                } else if (command === 'readEvents') {
                    resolve([]); // Return an empty array for readEvents
                } else {
                    resolve({});
                }
            });
        },
        getUserInfo: function() { return this._postMessage('getUserInfo'); },
        readEvents: function() { return this._postMessage('readEvents', {}); },
        postEvent: function(data) { return this._postMessage('postEvent', data); },
      };
    }
    
    const fetchUser = async () => {
      try {
        const user = await window.bbs.getUserInfo();
        setUserInfo(user);
      } catch (error) {
        console.error("Failed to fetch user info:", error);
      }
    };
    fetchUser();
  }, []);

  const handleStartGame = useCallback((self: Player, opponentInfo: UserInfo) => {
    if (!isAudioStarted) {
      Tone.start().then(() => {
        setIsAudioStarted(true);
        soundService.playMusic();
        setPlayer(self);
        setOpponent(opponentInfo);
        setGameState(GameState.Game);
      });
    } else {
      soundService.playMusic();
      setPlayer(self);
      setOpponent(opponentInfo);
      setGameState(GameState.Game);
    }
  }, [isAudioStarted]);

  const handleGameOver = useCallback(() => {
    soundService.stopMusic();
    setGameState(GameState.Lobby);
    setPlayer(null);
    setOpponent(null);
  }, []);

  const renderContent = () => {
    if (!userInfo) {
      return <div className="flex items-center justify-center h-screen text-xl">Loading User Info...</div>;
    }

    if (!isAudioStarted) {
      return (
        <div className="flex flex-col items-center justify-center h-screen">
          <h1 className="text-4xl font-bold mb-4">Fortress Overlord</h1>
          <p className="text-lg mb-8">A real-time strategy game.</p>
          <button
            onClick={() => Tone.start().then(() => setIsAudioStarted(true))}
            className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xl transition-transform transform hover:scale-105"
          >
            Click to Start Audio
          </button>
        </div>
      );
    }

    switch (gameState) {
      case GameState.Lobby:
        return <Lobby onStartGame={handleStartGame} userInfo={userInfo} />;
      case GameState.Game:
        if (player && opponent) {
          return <Game player={player} opponent={opponent} onGameOver={handleGameOver} />;
        }
        return <div className="text-red-500">Error: Player or opponent data is missing.</div>;
      default:
        return <div>Unknown game state</div>;
    }
  };

  return <div className="w-full h-screen">{renderContent()}</div>;
};

// Mock window.bbs for local development outside of Axon environment
declare global {
    interface Window {
        bbs: any;
    }
}


export default App;
