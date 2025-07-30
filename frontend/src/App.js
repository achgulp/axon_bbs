// Full path: axon_bbs/frontend/src/App.js
import React, { useState, useEffect } from 'react';
import apiClient from './apiClient';
import LoginScreen from './components/LoginScreen';
import RegisterScreen from './components/RegisterScreen';
import MessageList from './components/MessageList';
import UnlockForm from './components/UnlockForm';

const Header = ({ text }) => <div className="text-2xl font-bold text-gray-200 mb-4 pb-2 border-b border-gray-600">{text}</div>;
const SideBarButton = ({ onClick, children, className = '' }) => (
  <button onClick={onClick} className={`w-full text-left py-2 px-4 rounded hover:bg-gray-700 text-gray-300 transition duration-150 ease-in-out ${className}`}>
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
  const [isIdentityUnlocked, setIdentityUnlocked] = useState(false);
  const [needsUnlock, setNeedsUnlock] = useState(false);
  const setAuthToken = (newToken) => {
    if (newToken) {
      localStorage.setItem('token', newToken);
    } else {
      localStorage.removeItem('token');
      setIdentityUnlocked(false);
      // Lock identity on logout
    }
    setToken(newToken);
  };
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);
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
  };
  const handleUnlockSuccess = () => {
    setIdentityUnlocked(true);
    setNeedsUnlock(false);
  };
  if (!token) {
    return (
      <div className="bg-gray-800 min-h-screen">
        {authView === 'login' ? (
          <LoginScreen onLogin={setAuthToken} onNavigateToRegister={() => setAuthView('register')} />
        ) : (
          <RegisterScreen onRegisterSuccess={() => setAuthView('login')} onNavigateToLogin={() => setAuthView('login')} />
        )}
      </div>
    );
  }

  const renderMainContent = () => {
    if (selectedBoard) {
      return <MessageList board={selectedBoard} onBack={() => setSelectedBoard(null)} isIdentityUnlocked={isIdentityUnlocked} setNeedsUnlock={setNeedsUnlock} />;
    }
    return <MessageBoardList onSelectBoard={handleSelectBoard} />;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-300 font-sans">
      {needsUnlock && <UnlockForm onUnlock={handleUnlockSuccess} onCancel={() => setNeedsUnlock(false)} />}

      <div className="flex flex-col md:flex-row">
        <div className="w-full md:w-60 bg-gray-800 p-4 border-r border-gray-700 flex-shrink-0">
          <div className="flex items-center text-2xl font-bold text-white mb-6">
            <img src="/axon.png" alt="Axon logo" className="h-8 w-8 mr-3"/>
            <h2>Axon BBS</h2>
          </div>
          <nav className="space-y-2">
            <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">Menu</h3>
              <SideBarButton onClick={() => setSelectedBoard(null)}>Message Boards</SideBarButton>
              <SideBarButton onClick={() => alert("Private Mail not yet implemented.")}>Private Mail</SideBarButton>
            </div>
            <div className="p-2">
              <h3 className="font-semibold text-gray-400 mb-2">User</h3>
              <SideBarButton
                onClick={() => setNeedsUnlock(true)}
                className={isIdentityUnlocked ? 'text-green-400' : 'text-yellow-400'}
              >
                {isIdentityUnlocked ? '✓ Identity Unlocked' : '✗ Unlock Identity'}
              </SideBarButton>
              <SideBarButton onClick={() => alert("Profile not yet implemented.")}>Profile</SideBarButton>
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
