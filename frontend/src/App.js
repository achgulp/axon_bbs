// axon_bbs/frontend/src/App.js
import React, { useState, useEffect } from 'react';
import apiClient from './apiClient';
// import AnsiViewer from './components/AnsiViewer';  // Comment out or remove if not used
import LoginScreen from './components/LoginScreen';
import RegisterScreen from './components/RegisterScreen';
import MessageList from './components/MessageList';

// --- Helper Components ---
const Header = ({ text }) => <div className="text-4xl font-bold text-white mb-6 pb-2 border-b-2 border-gray-600">{text}</div>;
const Button = ({ onClick, children, className = 'bg-blue-600 hover:bg-blue-700' }) => (
    <button onClick={onClick} className={`${className} text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out w-full mb-2`}>
        {children}
    </button>
);
const BackButton = ({ onClick }) => <button onClick={onClick} className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded transition duration-300 ease-in-out w-full mt-4">Back</button>;

// --- API-Driven Components ---
const MessageBoardList = ({ onSelectBoard, onBack }) => {
  const [boards, setBoards] = useState([]);
  useEffect(() => {
    apiClient.get('/api/boards/').then(response => setBoards(response.data));
  }, []);
  return (
    <div>
      <Header text="Message Boards" />
      {boards.map(board => <Button key={board.id} onClick={() => onSelectBoard(board.id, board.name)}>{board.name}</Button>)}
      <BackButton onClick={onBack} />
    </div>
  );
};

const FileAreaList = ({ onBack }) => {
    return (
        <div>
            <Header text="File Areas" />
            <p className="text-gray-400 mb-4">File area functionality is not yet implemented.</p>
            <BackButton onClick={onBack} />
        </div>
    );
};

// --- Main App Component ---
function App() {
    const [token, setToken] = useState(localStorage.getItem('token'));
    const [authView, setAuthView] = useState('login');
    const [view, setView] = useState('main');
    const [selectedBoard, setSelectedBoard] = useState({ id: null, name: '' });

    const setAuthToken = (newToken) => {
        if (newToken) {
            localStorage.setItem('token', newToken);
        } else {
            localStorage.removeItem('token');
        }
        // The apiClient now handles headers automatically, so this line is removed.
        setToken(newToken);
    };

    useEffect(() => {
        const storedToken = localStorage.getItem('token');
        if (storedToken) {
            setToken(storedToken);
        }
    }, []);

    const handleLogout = () => {
        setAuthToken(null);
        setView('main');
    };
    
    const handleSelectBoard = (boardId, boardName) => {
        setSelectedBoard({ id: boardId, name: boardName });
    };

    if (!token) {
        if (authView === 'login') {
            return <LoginScreen onLogin={setAuthToken} onNavigateToRegister={() => setAuthView('register')} />;
        } else {
            return <RegisterScreen onRegisterSuccess={() => setAuthView('login')} onNavigateToLogin={() => setAuthView('login')} />;
        }
    }

    const renderBbsContent = () => {
        if (selectedBoard.id) {
            return (
                <div>
                    <Header text={`Board: ${selectedBoard.name}`} />
                    <MessageList boardId={selectedBoard.id} boardName={selectedBoard.name} />
                    <BackButton onClick={() => setSelectedBoard({ id: null, name: '' })} />
                </div>
            );
        }

        switch(view) {
            case 'messages':
                return <MessageBoardList onSelectBoard={handleSelectBoard} onBack={() => setView('main')} />;
            case 'files':
                return <FileAreaList onBack={() => setView('main')} />;
            default: // 'main' menu
                return (
                    <div>
                        <Header text="Main Menu" />
                        <Button onClick={() => setView('messages')}>Message Boards</Button>
                        <Button onClick={() => setView('files')}>File Areas</Button>
                        <Button onClick={() => setView('mail')}>Private Mail</Button>
                        <Button onClick={handleLogout} className="bg-red-600 hover:bg-red-700 mt-4">
                            Logout
                        </Button>
                    </div>
                );
        }
    };
    
    return (
        <div className="bg-gray-900 text-gray-300 min-h-screen p-8">
            <div className="max-w-2xl mx-auto">
                <h1 className="text-5xl font-bold text-white text-center mb-12">Axon BBS</h1>
                {renderBbsContent()}
            </div>
        </div>
    );
}

export default App;
