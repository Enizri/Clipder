import React, { useState } from 'react';
import { api } from '../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTwitchLogin = async () => {
    setError('');
    setLoading(true);
    try {
      const { authorization_url } = await api.getTwitchLoginUrl();
      window.location.href = authorization_url;
    } catch {
      setError('Could not reach Twitch. Please try again.');
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} aria-modal="true" role="dialog">
      <div className="auth-modal twitch-auth-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        <div className="twitch-auth-logo">
          {/* Twitch glitch logo */}
          <svg width="48" height="48" viewBox="0 0 24 24" fill="#9146FF" aria-hidden="true">
            <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z" />
          </svg>
        </div>

        <h2 className="twitch-auth-title">Sign in with Twitch</h2>
        <p className="twitch-auth-subtitle">
          Vote on clips, join the leaderboard, and make your picks count.
        </p>

        {error && <div className="error-msg">{error}</div>}

        <button
          className="twitch-login-btn"
          onClick={handleTwitchLogin}
          disabled={loading}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span
                className="video-loading active"
                style={{ width: 18, height: 18, borderWidth: 2, marginRight: 8 }}
              />
              Connecting...
            </>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z" />
              </svg>
              Login with Twitch
            </>
          )}
        </button>
      </div>
    </div>
  );
};
