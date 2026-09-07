import React, { useState } from 'react';
import { api } from '../api/client';

interface TwitchAuthWallProps {
  /** Called if we want to show the lighter auth modal instead (optional). */
  onShowAuth?: () => void;
}

/**
 * Full-screen hard block shown after a guest exhausts their 15 free swipes.
 * No dismiss — must authenticate to continue.
 */
export const TwitchAuthWall: React.FC<TwitchAuthWallProps> = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
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

  return (
    <div className="auth-wall-overlay" aria-modal="true" role="dialog" aria-label="Login required">
      <div className="auth-wall-card">
        {/* Decorative gradient orbs */}
        <div className="auth-wall-orb auth-wall-orb-1" aria-hidden="true" />
        <div className="auth-wall-orb auth-wall-orb-2" aria-hidden="true" />

        <div className="auth-wall-icon" aria-hidden="true">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="#9146FF">
            <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z" />
          </svg>
        </div>

        <h2 className="auth-wall-title">You're on a roll!</h2>
        <p className="auth-wall-subtitle">
          Connect with Twitch to make your votes count and keep swiping — it only takes a second.
        </p>

        {error && <div className="error-msg" style={{ marginBottom: '16px' }}>{error}</div>}

        <button
          className="twitch-login-btn auth-wall-btn"
          onClick={handleLogin}
          disabled={loading}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span
                className="video-loading active"
                style={{ width: 18, height: 18, borderWidth: 2, marginRight: 8 }}
              />
              Connecting to Twitch...
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

        <p className="auth-wall-fine-print">Free · No passwords · Just your Twitch account</p>
      </div>
    </div>
  );
};
