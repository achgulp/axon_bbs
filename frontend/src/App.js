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


// Full path: axon_bbs/frontend/src/App.js
import React, { useState, useEffect } from 'react';
import apiClient from './apiClient';
import LoginScreen from './components/LoginScreen';
import RegisterScreen from './components/RegisterScreen';
import RecoveryScreen from './components/RecoveryScreen';
import MessageList from './components/MessageList';
import ProfileScreen from './components/ProfileScreen';
import AppletView from './components/AppletView';
import HighScoreBoard from './components/HighScoreBoard';
import ModerationDashboard from './components/ModerationDashboard';
import PrivateMessageClient from './components/PrivateMessageClient';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const SideBarButton = ({ onClick, children, disabled, className = '' }) => (
  <button onClick={onClick} disabled={disabled} className={`w-full text-left py-2 px-4 rounded hover:bg-gray-700 text-gray-300 transition duration-150 ease-in-out disabled:text-gray-500 disabled:cursor-not-allowed ${className}`}>
    {children}
  </button>
);

const MessageBoardList = ({ onSelectBoard }) => {
  const [boards, setBoards] = useState([]);
  useEffect(() => {
    apiClient.get('/api/boards/')
      .then(response => setBoards(response.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div>
      <Header text="Message Boards" />
      <div className="space-y-2">
        {boards.map(board => (
          <button
            key={board.id}
            onClick={() => onSelectBoard(board.id, board.name)}
            className="w-full text-left p-3 rounded bg-gray-800 hover:bg-gray-700 border border-gray-700"
          >
            <h3 className="font-bold text-gray-200">{board.name}</h3>
            <p className="text-sm text-gray-400">{board.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
};


function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [authView, setAuthView] = useState('login');
  const [selectedBoard, setSelectedBoard] = useState(null);
  // DELETED: State for manual unlock is no longer needed.
  const [currentView, setCurrentView] = useState('boards');
  const [pmRecipient, setPmRecipient] = useState(null);
  const [lastPlayedGame, setLastPlayedGame] = useState(null);
  const [profile, setProfile] = useState(null);
  const [displayTimezone, setDisplayTimezone] = useState('UTC');

  const setAuthToken = (newToken) => {
    if (newToken) {
      localStorage.setItem('token', newToken);
    } else {
      localStorage.removeItem('token');
      // DELETED: No longer need to manage unlock state on logout
      setProfile(null);
    }
    setToken(newToken);
  };

  useEffect(() => {
    const fetchProfile = () => {
        apiClient.get('/api/user/profile/')
            .then(response => setProfile(response.data))
            .catch(err => console.error("Could not fetch user profile", err));
    };
    const fetchTimezone = () => {
        apiClient.get('/api/config/timezone/')
            .then(response => {
                setDisplayTimezone(response.data.timezone);
                console.log("Display timezone set to:", response.data.timezone);
            })
            .catch(err => console.error("Could not fetch display timezone", err));
    };

    if (token) {
      fetchProfile();
    }
    fetchTimezone(); 
  }, [token]);

  const handleLogout = async () => {
    try {
      await apiClient.post('/api/logout/');
    } catch (err) {
      console.error("Failed to clear server session, logging out client-side anyway.", err);
    } finally {
      setAuthToken(null);
    }
  };

  const handleSelectBoard = (boardId, boardName) => {
    setSelectedBoard({ id: boardId, name: boardName });
    setCurrentView('boards');
  };

  const handleViewChange = (view) => {
    setSelectedBoard(null);
    setPmRecipient(null);
    setCurrentView(view);
  };

  const handleStartPrivateMessage = (pubkey, displayName) => {
    setPmRecipient({ pubkey: pubkey, displayName: displayName });
    setCurrentView('pm');
  };

  // DELETED: handleUnlockSuccess is no longer needed.

  if (!token) {
    return (
      <div className="bg-gray-800 min-h-screen">
        {authView === 'login' && <LoginScreen onLogin={setAuthToken} onNavigateToRegister={() => setAuthView('register')} onNavigateToRecovery={() => setAuthView('recovery')} />}
        {authView === 'register' && <RegisterScreen onRegisterSuccess={() => setAuthView('login')} onNavigateToLogin={() => setAuthView('login')} />}
        {authView === 'recovery' && <RecoveryScreen onNavigateToLogin={() => setAuthView('login')} />}
      </div>
    );
  }

  const renderMainContent = () => {
    // MODIFIED: If an identity_locked error ever occurs, log the user out.
    const onIdentityLocked = () => {
        alert("Your session's identity key has expired or is invalid. Please log in again to create a new session.");
        handleLogout();
    };

    if (currentView === 'profile') {
      return <ProfileScreen />;
    }
    if (currentView === 'pm') {
      return <PrivateMessageClient key={pmRecipient ? pmRecipient.pubkey : 'new'} initialRecipient={pmRecipient} displayTimezone={displayTimezone} onIdentityLocked={onIdentityLocked} />;
    }
    if (currentView === 'applets') {
      return <AppletView onLaunchGame={setLastPlayedGame} />;
    }
    if (currentView === 'high_scores' && lastPlayedGame) {
      return <HighScoreBoard applet={lastPlayedGame} onBack={() => handleViewChange('applets')} displayTimezone={displayTimezone} />;
    }
    if (currentView === 'moderation') {
      return <ModerationDashboard displayTimezone={displayTimezone} onStartPrivateMessage={handleStartPrivateMessage} onIdentityLocked={onIdentityLocked} />;
    }
    if (selectedBoard) {
      return <MessageList board={selectedBoard} onBack={() => setSelectedBoard(null)} onStartPrivateMessage={handleStartPrivateMessage} displayTimezone={displayTimezone} onIdentityLocked={onIdentityLocked} />;
    }
    return <MessageBoardList onSelectBoard={handleSelectBoard} />;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-300 font-sans">
      {/* DELETED: The UnlockForm modal has been removed */}

      <div className="flex flex-col md:flex-row">
        <div className="w-full md:w-60 bg-gray-800 p-4 border-r border-gray-700 flex-shrink-0">
          <div className="flex items-center text-2xl font-bold text-white mb-6">
            <img src="/axon.png" alt="Axon logo" className="h-12 w-12 mr-3"/>
            <h2>Axon BBS</h2>
          </div>
          <nav className="space-y-2">
            <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">Menu</h3>
              <SideBarButton onClick={() => handleViewChange('boards')}>Message Boards</SideBarButton>
              <SideBarButton onClick={() => handleViewChange('pm')}>Private Mail</SideBarButton>
              <SideBarButton onClick={() => handleViewChange('applets')}>Applets</SideBarButton>
              <SideBarButton 
                onClick={() => handleViewChange('high_scores')}
                disabled={!lastPlayedGame}
                title={!lastPlayedGame ? "Play a game first to see high scores" : "View high scores for the last game you played"}
              >
                High Scores
              </SideBarButton>
              {profile?.is_moderator && (
                <SideBarButton onClick={() => handleViewChange('moderation')}>Moderation</SideBarButton>
              )}
            </div>
            <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">User</h3>
              {/* DELETED: The "Unlock Identity" button has been removed. */}
              <SideBarButton onClick={() => handleViewChange('profile')}>Profile</SideBarButton>
              <SideBarButton onClick={handleLogout}>Logout</SideBarButton>
            </div>
          </nav>
        </div>
        <main className="flex-1 p-6">
           {renderMainContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
