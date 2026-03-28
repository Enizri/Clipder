import React from 'react';
import type { User } from '../types';

interface ProfilePageProps {
  user: User | null;
  onUserUpdate: (user: User) => void;
  onShowAuth: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({ user, onShowAuth }) => {
  const handleLoginWithTwitch = async () => {
    onShowAuth();
  };

  return (
    <div id="profile" className="view-section active">
      <div className="list-container">
        <h2 className="section-title">Profile</h2>

        {user ? (
          <div className="profile-content">
            <div className="profile-card">
              <div className="profile-avatar">{user.username.charAt(0).toUpperCase()}</div>
              <div className="profile-info">
                <h3>{user.username}</h3>
                <span className="role-badge">{user.role}</span>
                {user.is_pro && <span className="pro-badge"><span className="pro-badge-text">PRO</span></span>}
              </div>
            </div>

            <div className="twitch-section">
              <h4>Twitch Account</h4>
              {/* Every user is Twitch-linked by definition in Twitch-only auth */}
              {user.twitch_username ? (
                <div className="twitch-connected">
                  <span>
                    Connected as: <strong>@{user.twitch_username}</strong>
                  </span>
                </div>
              ) : (
                <p className="hint-text">No Twitch account linked (unexpected — please re-login).</p>
              )}
            </div>

            <div className="following-section">
              <h4>My Streamers</h4>
              <p className="section-subtitle">
                Streamers you want to see in your swipe feed
              </p>
              <p className="hint-text">
                Sync your Twitch follows to personalise your feed.
              </p>
            </div>
          </div>
        ) : (
          <div className="auth-prompt">
            <p>Login with Twitch to access your profile</p>
            <button className="twitch-login-btn" style={{ maxWidth: 260, margin: '16px auto 0' }} onClick={handleLoginWithTwitch}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z" />
              </svg>
              Login with Twitch
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
