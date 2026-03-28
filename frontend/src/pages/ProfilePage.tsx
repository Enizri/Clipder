import React from 'react';
import { api } from '../api/client';
import type { User } from '../types';

interface ProfilePageProps {
  user: User | null;
  onUserUpdate: (user: User) => void;
  onShowAuth: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({ user, onUserUpdate, onShowAuth }) => {
  const handleLinkTwitch = async () => {
    try {
      const { authorization_url } = await api.getTwitchLoginUrl();
      const popup = window.open(authorization_url, 'Twitch OAuth', 'width=600,height=700');

      const handleMessage = (event: MessageEvent) => {
        if (event.data?.type === 'twitch_linked') {
          window.removeEventListener('message', handleMessage);
          api.getMe().then(onUserUpdate).catch(() => {});
          popup?.close();
        }
      };
      window.addEventListener('message', handleMessage);
    } catch (err) {
      console.error('Failed to start Twitch OAuth:', err);
    }
  };

  const handleUnlinkTwitch = async () => {
    try {
      await api.unlinkTwitch();
      window.location.reload();
    } catch (err) {
      console.error('Failed to unlink Twitch:', err);
    }
  };

  return (
    <div id="profile" className="view-section active">
      <div className="list-container">
        <h2 className="section-title">👤 Profile</h2>

        {user ? (
          <div className="profile-content">
            <div className="profile-card">
              <div className="profile-avatar">{user.username.charAt(0).toUpperCase()}</div>
              <div className="profile-info">
                <h3>{user.username}</h3>
                <p>{user.email}</p>
                <span className="role-badge">{user.role}</span>
              </div>
            </div>

            <div className="twitch-section">
              <h4>📺 Twitch Account</h4>
              {user.twitch_username ? (
                <div className="twitch-connected">
                  <span>
                    Connected as: <strong>@{user.twitch_username}</strong>
                  </span>
                  <button className="btn-small btn-outline" onClick={handleUnlinkTwitch}>
                    Unlink
                  </button>
                </div>
              ) : (
                <button className="btn-small btn-primary" onClick={handleLinkTwitch}>
                  Connect Twitch Account
                </button>
              )}
            </div>

            <div className="following-section">
              <h4>⭐ My Streamers</h4>
              <p className="section-subtitle">
                Streamers you want to see in your swipe feed
              </p>
              <p className="hint-text">
                Connect your Twitch account above to sync your follows automatically!
              </p>
            </div>
          </div>
        ) : (
          <div className="auth-prompt">
            <p>Please login to access your profile</p>
            <button className="btn-primary" onClick={onShowAuth}>
              Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
