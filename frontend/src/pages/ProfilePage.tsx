import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ForYouChannelPicker } from '../components/ForYouChannelPicker';
import { api } from '../api/client';
import type { Streamer, User } from '../types';
import { filterFollowedStreamersByPrefix } from '../utils/followSearch';

const isViteDev = (): boolean =>
  Boolean((import.meta as { env?: { DEV?: boolean } }).env?.DEV);

interface ProfilePageProps {
  user: User | null;
  onUserUpdate: (user: User) => void;
  onShowAuth: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({ user, onUserUpdate: _onUserUpdate, onShowAuth }) => {
  const [streamers, setStreamers] = useState<Streamer[]>([]);
  const [search, setSearch] = useState('');
  const [loadingList, setLoadingList] = useState(false);
  const [forYouSaving, setForYouSaving] = useState(false);
  const [syncBusy, setSyncBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadFollowing = useCallback(async () => {
    if (!user) return;
    setLoadingList(true);
    try {
      const rows = await api.getFollowing();
      setStreamers(Array.isArray(rows) ? rows : []);
    } catch (err) {
      if (isViteDev()) console.warn('getFollowing failed', err);
      setStreamers([]);
    } finally {
      setLoadingList(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user) {
      setStreamers([]);
      return;
    }
    void loadFollowing();
  }, [user, loadFollowing]);

  const refreshFollowingQuiet = useCallback(async () => {
    if (!user) return;
    try {
      const rows = await api.getFollowing();
      setStreamers(Array.isArray(rows) ? rows : []);
    } catch (err) {
      if (isViteDev()) console.warn('getFollowing failed', err);
    }
  }, [user]);

  const mergeForYouInclude = async (idsToInclude: string[]) => {
    if (!user) return;
    setForYouSaving(true);
    try {
      const rows = await api.getFollowing();
      const list = Array.isArray(rows) ? rows : [];
      const base = new Set(list.filter((x) => x.include_in_for_you).map((x) => x.streamer_id));
      idsToInclude.forEach((id) => base.add(id));
      await api.setForYouStreamers([...base]);
      await refreshFollowingQuiet();
    } catch (err) {
      if (isViteDev()) console.warn('For You merge failed', err);
    } finally {
      setForYouSaving(false);
    }
  };

  /**
   * `silent` = per-row checkbox: optimistic UI, no full-list lock or loading spinner.
   * `blocking` = bulk actions (e.g. For You: all) — disables toolbar while saving.
   */
  const persistForYouIds = async (ids: string[], mode: 'silent' | 'blocking' = 'silent') => {
    if (!user) return;
    const idSet = new Set(ids);
    if (mode === 'silent') {
      setStreamers((prev) =>
        prev.map((row) => ({ ...row, include_in_for_you: idSet.has(row.streamer_id) })),
      );
    } else {
      setForYouSaving(true);
    }
    try {
      await api.setForYouStreamers(ids);
      await refreshFollowingQuiet();
    } catch (err) {
      if (isViteDev()) console.warn('For You preferences failed', err);
      await refreshFollowingQuiet();
    } finally {
      if (mode === 'blocking') setForYouSaving(false);
    }
  };

  const handleSyncFromTwitch = async () => {
    if (!user?.twitch_username) return;
    setSyncBusy(true);
    setStatusMessage(null);
    try {
      const res = await api.syncFollows();
      await loadFollowing();
      setStatusMessage(
        res.added > 0
          ? `Added ${res.added} channel${res.added === 1 ? '' : 's'} from Twitch.`
          : 'Already up to date with your Twitch follows.',
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Sync failed';
      setStatusMessage(msg);
      if (isViteDev()) console.warn('syncFollows failed', err);
    } finally {
      setSyncBusy(false);
    }
  };

  const handleRemove = async (streamerId: string) => {
    if (!user) return;
    try {
      await api.removeFollowing(streamerId);
      await loadFollowing();
    } catch (err) {
      if (isViteDev()) console.warn('removeFollowing failed', err);
    }
  };

  const filtered = useMemo(
    () => filterFollowedStreamersByPrefix(streamers, search),
    [streamers, search],
  );

  const handleLoginWithTwitch = () => {
    onShowAuth();
  };

  return (
    <div id="profile" className="view-section active profile-page-root">
      <div className="list-container profile-list-outer">
        <h2 className="section-title">Profile</h2>

        {user ? (
          <div className="profile-content">
            <div className="profile-card">
              <div className="profile-avatar">{user.username.charAt(0).toUpperCase()}</div>
              <div className="profile-info">
                <h3>{user.username}</h3>
                <span className="role-badge">{user.role}</span>
                {user.is_pro && (
                  <span className="pro-badge">
                    <span className="pro-badge-text">PRO</span>
                  </span>
                )}
              </div>
            </div>

            <div className="twitch-section">
              <h4>Twitch account</h4>
              {user.twitch_username ? (
                <div className="twitch-connected">
                  <span>
                    Connected as: <strong>@{user.twitch_username}</strong>
                  </span>
                  <p className="hint-text profile-hint-tight">
                    When you sign in with Twitch, we import the channels you follow. Use the list below to search,
                    remove channels, or choose who appears in For You.
                  </p>
                </div>
              ) : (
                <p className="hint-text">No Twitch account linked (unexpected — please re-login).</p>
              )}
            </div>

            <div className="following-section profile-following-section">
              <div className="profile-following-header">
                <div>
                  <h4>Channels you follow</h4>
                  <p className="section-subtitle">Synced from Twitch — manage For You and your swipe feed here</p>
                </div>
                <button
                  type="button"
                  className="profile-sync-twitch-btn"
                  disabled={syncBusy || !user.twitch_username}
                  onClick={() => void handleSyncFromTwitch()}
                >
                  {syncBusy ? 'Syncing…' : 'Refresh from Twitch'}
                </button>
              </div>

              {statusMessage && <p className="profile-sync-status">{statusMessage}</p>}

              <div className="for-you-toolbar profile-following-toolbar">
                <ForYouChannelPicker
                  value={search}
                  onChange={setSearch}
                  streamers={streamers}
                  onMergeForYou={mergeForYouInclude}
                  onRefreshFollowing={refreshFollowingQuiet}
                  busy={forYouSaving}
                  placeholder="Type to find follows or search Twitch…"
                  ariaLabel="Search channels for your list and For You"
                />
                <button
                  type="button"
                  className="for-you-select-all"
                  disabled={forYouSaving || streamers.length === 0}
                  onClick={() =>
                    void persistForYouIds(
                      streamers.map((s) => s.streamer_id),
                      'blocking',
                    )
                  }
                >
                  For You: all
                </button>
              </div>

              {forYouSaving && <p className="for-you-saving">Updating For You…</p>}

              {loadingList && <p className="hint-text">Loading your follows…</p>}

              {!loadingList && streamers.length === 0 && (
                <p className="hint-text">
                  No channels yet. They should appear right after you connect with Twitch — try{' '}
                  <strong>Refresh from Twitch</strong> if the list is empty.
                </p>
              )}

              {!loadingList && streamers.length > 0 && filtered.length > 0 && (
                <ul className="for-you-list profile-following-list" aria-label="Followed channels">
                  {filtered.map((s) => (
                    <li key={s.streamer_id} className="for-you-row profile-streamer-row">
                      <label className="for-you-check-label profile-streamer-label">
                        <input
                          type="checkbox"
                          checked={s.include_in_for_you}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            const base = new Set(
                              streamers.filter((x) => x.include_in_for_you).map((x) => x.streamer_id),
                            );
                            if (checked) base.add(s.streamer_id);
                            else base.delete(s.streamer_id);
                            void persistForYouIds([...base], 'silent');
                          }}
                        />
                        <span>{s.streamer_name}</span>
                      </label>
                      <span className="profile-for-you-hint">For You</span>
                      <button
                        type="button"
                        className="profile-remove-streamer-btn"
                        aria-label={`Remove ${s.streamer_name} from list`}
                        onClick={() => void handleRemove(s.streamer_id)}
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {streamers.length > 0 && filtered.length === 0 && (
                <p className="hint-text">No channels match your search.</p>
              )}
            </div>
          </div>
        ) : (
          <div className="auth-prompt">
            <p>Login with Twitch to access your profile</p>
            <button
              className="twitch-login-btn"
              style={{ maxWidth: 260, margin: '16px auto 0' }}
              onClick={handleLoginWithTwitch}
            >
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
