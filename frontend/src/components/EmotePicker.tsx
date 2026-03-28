import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import type { EmoteResponse } from '../types';

type EmoteTab = 'twitch' | 'bttv' | '7tv';

interface EmotePickerProps {
  onSelect: (url: string, code: string) => void;
  onClose: () => void;
}

export const EmotePicker: React.FC<EmotePickerProps> = ({ onSelect, onClose }) => {
  const [activeTab, setActiveTab] = useState<EmoteTab>('twitch');
  const [emotes, setEmotes] = useState<EmoteResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getEmotes()
      .then(setEmotes)
      .catch(() => {
        // Emote load failing is non-fatal — show empty grid
      })
      .finally(() => setLoading(false));
  }, []);

  const currentEmotes = useMemo(() => {
    if (!emotes) return [];
    if (activeTab === 'twitch') return emotes.twitch;
    if (activeTab === 'bttv') return emotes.bttv;
    if (activeTab === '7tv') return emotes.seventv;
    return [];
  }, [emotes, activeTab]);

  return (
    <div className="emote-picker-popup">
      <div className="emote-picker-header">
        <div className="emote-tabs">
          {(['twitch', 'bttv', '7tv'] as EmoteTab[]).map((tab) => (
            <button
              key={tab}
              className={`emote-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === '7tv' ? '7TV' : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        <button className="emote-picker-close" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="emote-grid">
        {loading ? (
          <div className="emote-loading">
            <div className="spinner" />
            <span>Loading emotes...</span>
          </div>
        ) : currentEmotes.length > 0 ? (
          currentEmotes.map((emote) => (
            <div
              key={emote.id}
              className="emote-option"
              onClick={() => onSelect(emote.url, emote.code)}
              title={emote.code}
            >
              <img
                src={emote.url}
                alt={emote.code}
                loading="lazy"
                onError={(e) => {
                  // Emote CDNs occasionally 404 — hide the broken image silently
                  (e.currentTarget as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
          ))
        ) : (
          <div className="emote-empty">No emotes available</div>
        )}
      </div>
    </div>
  );
};
