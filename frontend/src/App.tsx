import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import { api } from './api/client';
import type { User, Comment } from './types';
import { AuthModal } from './components/AuthModal';
import { CommentsPanel } from './components/CommentsPanel';
import { SwipePage } from './pages/SwipePage';
import { LeaderboardPage } from './pages/LeaderboardPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AiEditorPage } from './pages/AiEditorPage';
import { ProfilePage } from './pages/ProfilePage';

// ==============================================================================
// HEADER (inner — has access to useNavigate)
// ==============================================================================

interface HeaderProps {
  user: User | null;
  onShowAuth: () => void;
  onLogout: () => void;
}

const Header: React.FC<HeaderProps> = ({ user, onShowAuth, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/');
  };

  return (
    <header>
      <h1>
        Clip<span className="logo-accent">der</span>
        {user && (user.role === 'PRO' || user.role === 'ADMIN') && ' Pro'}
      </h1>
      <nav className="nav-tabs">
        <NavLink className={({ isActive }) => `tab-btn${isActive ? ' active' : ''}`} to="/" end>
          Swipe &amp; Vote
        </NavLink>
        <NavLink className={({ isActive }) => `tab-btn${isActive ? ' active' : ''}`} to="/leaderboard">
          Leaderboard
        </NavLink>
        <NavLink className={({ isActive }) => `tab-btn${isActive ? ' active' : ''}`} to="/analytics">
          📊 Analytics
        </NavLink>
        <NavLink className={({ isActive }) => `tab-btn${isActive ? ' active' : ''}`} to="/ai-editor">
          🚀 AI Editor
        </NavLink>
        <NavLink className={({ isActive }) => `tab-btn${isActive ? ' active' : ''}`} to="/profile">
          Profile
        </NavLink>
      </nav>
      <div className="auth-section">
        {user ? (
          <div className="user-menu">
            {(user.role === 'PRO' || user.role === 'ADMIN') && (
              <span className="pro-badge">
                <span className="pro-badge-text">👑</span>
                <span className="pro-badge-label">{user.role}</span>
              </span>
            )}
            {user.twitch_username && (
              <span className="twitch-badge">📺 {user.twitch_username}</span>
            )}
            <button onClick={handleLogout}>Logout</button>
          </div>
        ) : (
          <button className="auth-btn" onClick={onShowAuth}>
            Login
          </button>
        )}
      </div>
    </header>
  );
};

// ==============================================================================
// APP ROOT
// ==============================================================================

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [activeCommentClip, setActiveCommentClip] = useState<{ id: string; title: string } | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);

  // Restore session from stored JWT and handle Twitch OAuth callback (?token=)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const callbackToken = params.get('token');

    if (callbackToken) {
      // Fresh token from Twitch OAuth redirect — store and clean URL
      localStorage.setItem('token', callbackToken);
      window.history.replaceState({}, '', window.location.pathname);
    }

    const token = callbackToken || localStorage.getItem('token');
    if (token) {
      api
        .getMe()
        .then(setUser)
        .catch(() => localStorage.removeItem('token'));
    }
  }, []);

  // Keep document title in sync with user role
  useEffect(() => {
    document.title =
      user && (user.role === 'PRO' || user.role === 'ADMIN') ? 'Clipder Pro' : 'Clipder';
  }, [user]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const openComments = useCallback((clipId: string, title: string) => {
    setActiveCommentClip({ id: clipId, title });
    api
      .getComments(clipId)
      .then(setComments)
      .catch(() => setComments([]));
    setShowComments(true);
  }, []);

  const closeComments = useCallback(() => {
    setShowComments(false);
    setActiveCommentClip(null);
  }, []);

  const postComment = async (text: string) => {
    if (!activeCommentClip) return;
    try {
      await api.postComment(activeCommentClip.id, text);
      const updated = await api.getComments(activeCommentClip.id);
      setComments(updated);
    } catch {
      // Comment failed — leave the input as is so user can retry
    }
  };

  return (
    <BrowserRouter>
      <Header user={user} onShowAuth={() => setShowAuthModal(true)} onLogout={handleLogout} />

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
      />

      <CommentsPanel
        show={showComments}
        onClose={closeComments}
        activeClip={activeCommentClip}
        comments={comments}
        onPostComment={postComment}
      />

      <div className="app-container">
        <Routes>
          <Route path="/" element={<SwipePage user={user} onOpenComments={openComments} />} />
          <Route path="/leaderboard" element={<LeaderboardPage onOpenComments={openComments} />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/ai-editor" element={<AiEditorPage user={user} />} />
          <Route
            path="/profile"
            element={
              <ProfilePage
                user={user}
                onUserUpdate={setUser}
                onShowAuth={() => setShowAuthModal(true)}
              />
            }
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
