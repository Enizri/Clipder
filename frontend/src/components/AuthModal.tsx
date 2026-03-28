import React, { useState } from 'react';
import { api } from '../api/client';
import type { User } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogin: (token: string, user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onLogin }) => {
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password || (!isLoginMode && !username)) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      if (isLoginMode) {
        const res = await api.login(email, password);
        localStorage.setItem('token', res.access_token);
        onLogin(res.access_token, res.user);
        onClose();
      } else {
        const res = await api.register(username, email, password);
        localStorage.setItem('token', res.access_token);
        onLogin(res.access_token, res.user);
        onClose();
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} aria-modal="true" role="dialog">
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
        <h2>{isLoginMode ? 'Welcome Back' : 'Create Account'}</h2>
        <form onSubmit={handleSubmit}>
          {!isLoginMode && (
            <input
              aria-label="Username"
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          )}
          <input
            aria-label="Email"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div style={{ position: 'relative' }}>
            <input
              aria-label="Password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              style={{
                position: 'absolute',
                right: 10,
                top: 10,
                background: 'none',
                border: 'none',
                color: '#8b5cf6',
                cursor: 'pointer',
              }}
              aria-label="Toggle password visibility"
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button type="submit" disabled={loading} aria-busy={loading}>
            {loading ? (
              <>
                <span
                  className="video-loading active"
                  style={{ width: 18, height: 18, borderWidth: 2, marginRight: 8 }}
                />
                Sending...
              </>
            ) : isLoginMode ? (
              'Login'
            ) : (
              'Sign Up'
            )}
          </button>
        </form>
        <p className="auth-switch">
          {isLoginMode ? "Don't have an account? " : 'Already have an account? '}
          <button type="button" onClick={() => setIsLoginMode((m) => !m)}>
            {isLoginMode ? 'Sign Up' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
};
