import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api, createLeaderboardSocket } from './api/client';
import type { Clip, LeaderboardClip, AdminClip, Comment, EmoteResponse, GifResponse, User } from './types';
import { DemoVideo } from './DemoVideo';

type Tab = 'swipe' | 'leaderboard' | 'admin' | 'profile' | 'ai-editor';
type EmoteTab = 'twitch' | 'bttv' | '7tv' | 'gifs';

const videoUrlCache: Record<string, string> = {};

const getSeenClipIds = (): Set<string> => {
  const stored = localStorage.getItem('seenClipIds');
  return stored ? new Set(JSON.parse(stored)) : new Set();
};

const addSeenClipId = (clipId: string): void => {
  const seen = getSeenClipIds();
  seen.add(clipId);
  localStorage.setItem('seenClipIds', JSON.stringify([...seen]));
};

const ClipPreview = React.memo(function ClipPreview({ clip, onOpenTheater, children, isPreload }: { clip: Clip; onOpenTheater: () => void; children?: React.ReactNode; isPreload?: boolean }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(5);
  const [progress, setProgress] = useState(0);
  const [isHovering, setIsHovering] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchVideoUrl = useCallback(() => {
    if (videoSrc) return;
    if (videoUrlCache[clip.id]) {
      setVideoSrc(videoUrlCache[clip.id]);
      return;
    }
    setIsLoading(true);
    api.getVideoUrl(clip.id).then((data) => {
      if (data.video_url) {
        videoUrlCache[clip.id] = data.video_url;
        setVideoSrc(data.video_url);
      }
    }).catch(() => {})
      .finally(() => setIsLoading(false));
  }, [clip.id, videoSrc]);

  useEffect(() => {
    if (isPreload && !videoSrc && videoUrlCache[clip.id]) {
      setVideoSrc(videoUrlCache[clip.id]);
    }
  }, [isPreload, videoSrc, clip.id]);

  useEffect(() => {
    if (isHovering || isPreload) {
      fetchVideoUrl();
    }
  }, [isHovering, isPreload, fetchVideoUrl]);

  useEffect(() => {
    if (isHovering && !videoSrc && !isLoading) {
      fetchVideoUrl();
    }
  }, [isHovering, videoSrc, isLoading, fetchVideoUrl]);

  useEffect(() => {
    if (!videoSrc || !isHovering) return;
    const video = videoRef.current;
    if (!video) return;
    
    if (video.readyState >= 2) {
      video.volume = volume / 100;
      video.muted = false;
      video.play().catch(() => {});
      setIsPlaying(true);
    } else {
      const onCanPlay = () => {
        video.volume = volume / 100;
        video.muted = false;
        video.play().catch(() => {});
        setIsPlaying(true);
      };
      video.addEventListener('canplay', onCanPlay, { once: true });
    }
  }, [isHovering, videoSrc, volume]);

  useEffect(() => {
    if (!isHovering && isPlaying) {
      const video = videoRef.current;
      if (video) {
        video.pause();
        setIsPlaying(false);
      }
    }
  }, [isHovering, isPlaying]);

  const handleMouseEnter = () => {
    setIsHovering(true);
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
  };

  const handlePlayPause = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video || !videoSrc) return;
    if (isPlaying) {
      video.pause();
    } else {
      video.play().catch(() => {});
    }
    setIsPlaying(!isPlaying);
  };

  const handleFullscreen = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOpenTheater();
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (videoRef.current) {
      videoRef.current.muted = newMuted;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const vol = parseInt(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol / 100;
      if (vol === 0) {
        setIsMuted(true);
        videoRef.current.muted = true;
      } else if (isMuted && vol > 0) {
        setIsMuted(false);
        videoRef.current.muted = false;
      }
    }
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video) return;
    const val = parseFloat(e.target.value);
    video.currentTime = (val / 100) * video.duration;
    setProgress(val);
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video && video.duration) {
      const val = (video.currentTime / video.duration) * 100;
      setProgress(val);
    }
  };

  return (
    <div
      ref={containerRef}
      className="clip-preview"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="blur-bg-container">
        <img src={clip.thumbnail_url} alt="" draggable={false} />
      </div>
      <img src={clip.thumbnail_url} className="clip-thumbnail" alt={clip.title} draggable={false} 
           style={{ opacity: isPlaying ? 0 : 1 }} />
      
      <video
        ref={videoRef}
        src={videoSrc || undefined}
        className={`video-player ${isPlaying ? 'playing' : ''}`}
        loop
        muted={isMuted}
        playsInline
        onTimeUpdate={handleTimeUpdate}
        preload="auto"
      />
      
      <div className={`video-loading ${isLoading ? 'active' : ''}`}></div>
      
      <button className="fullscreen-btn" onClick={handleFullscreen} title="Theater Mode">⛶</button>
      <button className="play-pause-btn" onClick={handlePlayPause} title="Play/Pause">
        {isPlaying ? '⏸' : '▶'}
      </button>
      
      <div className="volume-control">
        <button className="volume-btn" onClick={toggleMute}><span>{volume === 0 ? '🔇' : '🔊'}</span></button>
        <input type="range" className="volume-slider" min="0" max="100" value={volume} onChange={handleVolumeChange} />
      </div>
      
      <div className="progress-container">
        <input
          type="range"
          className="progress-slider"
          min="0"
          max="100"
          step="0.1"
          value={progress}
          onChange={handleProgressChange}
          style={{ background: `linear-gradient(to right, #ec4899 ${progress}%, rgba(255, 255, 255, 0.2) ${progress}%)` }}
        />
      </div>
      
      {children}
    </div>
  );
});

const MiniThumb = React.memo(function MiniThumb({ clip, onOpenTheater, isHighlighted }: { clip: LeaderboardClip | AdminClip; onOpenTheater: () => void; isHighlighted?: boolean }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(5);
  const [isHovering, setIsHovering] = useState(false);

  const fetchVideoUrl = useCallback(() => {
    if (videoSrc) return;
    setIsLoading(true);
    api.getVideoUrl(clip.id).then((data) => {
      if (data.video_url) {
        videoUrlCache[clip.id] = data.video_url;
        setVideoSrc(data.video_url);
      }
    }).catch(() => {})
      .finally(() => setIsLoading(false));
  }, [clip.id, videoSrc]);

  useEffect(() => {
    if (isHovering) {
      fetchVideoUrl();
    }
  }, [isHovering, fetchVideoUrl]);

  useEffect(() => {
    if (isHovering && videoSrc) {
      const video = videoRef.current;
      if (!video) return;
      if (video.readyState >= 2) {
        video.volume = volume / 100;
        video.muted = isMuted || volume === 0;
        video.play().catch(() => {});
        setIsPlaying(true);
      } else {
        video.addEventListener('loadeddata', () => {
          video.volume = volume / 100;
          video.muted = isMuted || volume === 0;
          video.play().catch(() => {});
          setIsPlaying(true);
        }, { once: true });
      }
    } else if (videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, [isHovering, videoSrc, volume, isMuted]);

  const handleMouseEnter = () => {
    setIsHovering(true);
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
  };

  const togglePlay = (e: React.MouseEvent) => {
    e.stopPropagation();
    const video = videoRef.current;
    if (!video || !videoSrc) return;
    if (isPlaying) {
      video.pause();
    } else {
      video.play().catch(() => {});
    }
    setIsPlaying(!isPlaying);
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (videoRef.current) {
      videoRef.current.muted = newMuted;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const vol = parseInt(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol / 100;
      if (vol === 0) {
        setIsMuted(true);
        videoRef.current.muted = true;
      } else if (isMuted && vol > 0) {
        setIsMuted(false);
        videoRef.current.muted = false;
      }
    }
  };

  return (
    <div
      className={`thumb-container ${isLoading ? 'loading' : ''} ${isHighlighted ? 'highlighted' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <img src={clip.thumbnail_url} alt={clip.title} />
      <div className="mini-spinner"></div>
      <video ref={videoRef} src={videoSrc || undefined} className={isPlaying ? 'playing' : ''} loop muted playsInline />
      <div className="mini-controls">
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <button className="mini-btn" onClick={togglePlay}>{isPlaying ? '⏸' : '▶'}</button>
          <button className="mini-btn" onClick={toggleMute}>{volume === 0 ? '🔇' : '🔊'}</button>
          <input 
            type="range" 
            className="mini-volume" 
            min="0" 
            max="100" 
            value={volume} 
            onChange={handleVolumeChange}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
        <button className="mini-btn" onClick={onOpenTheater}>⛶</button>
      </div>
    </div>
  );
});

function EmotePicker({ onSelect, onClose }: { onSelect: (url: string, code: string) => void; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<EmoteTab>('twitch');
  const [emotes, setEmotes] = useState<EmoteResponse | null>(null);
  const [gifs, setGifs] = useState<GifResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEmotes();
  }, []);

  const loadEmotes = async () => {
    try {
      const data = await api.getEmotes();
      setEmotes(data);
    } catch (e) {
      console.error('Failed to load emotes:', e);
    } finally {
      setLoading(false);
    }
  };

  const searchGifs = useCallback(async (query: string) => {
    if (!query.trim()) {
      setGifs(null);
      return;
    }
    try {
      const data = await api.searchGifs(query);
      setGifs(data);
    } catch (e) {
      console.error('Failed to search gifs:', e);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'gifs' && searchQuery) {
      const timer = setTimeout(() => searchGifs(searchQuery), 300);
      return () => clearTimeout(timer);
    }
  }, [searchQuery, activeTab, searchGifs]);

  const handleSelect = (url: string, code: string) => {
    onSelect(url, code);
  };

  const currentEmotes = useMemo(() => {
    if (!emotes) return [];
    switch (activeTab) {
      case 'twitch': return emotes.twitch;
      case 'bttv': return emotes.bttv;
      case '7tv': return emotes.seventv;
      default: return [];
    }
  }, [emotes, activeTab]);

  return (
    <div className="emote-picker-popup">
      <div className="emote-picker-header">
        <div className="emote-tabs">
          <button className={`emote-tab ${activeTab === 'twitch' ? 'active' : ''}`} onClick={() => setActiveTab('twitch')}>Twitch</button>
          <button className={`emote-tab ${activeTab === 'bttv' ? 'active' : ''}`} onClick={() => setActiveTab('bttv')}>BTTV</button>
          <button className={`emote-tab ${activeTab === '7tv' ? 'active' : ''}`} onClick={() => setActiveTab('7tv')}>7TV</button>
          <button className={`emote-tab ${activeTab === 'gifs' ? 'active' : ''}`} onClick={() => setActiveTab('gifs')}>GIFs</button>
        </div>
        <button className="emote-picker-close" onClick={onClose}>✕</button>
      </div>
      
      {activeTab === 'gifs' && (
        <div className="emote-search">
          <input
            type="text"
            placeholder="Search GIFs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      )}

      <div className="emote-grid">
        {loading ? (
          <div className="emote-loading">
            <div className="spinner"></div>
            <span>Loading emotes...</span>
          </div>
        ) : activeTab === 'gifs' ? (
          gifs?.gifs && gifs.gifs.length > 0 ? (
            gifs.gifs.map((gif) => (
              <div key={gif.id} className="emote-option gif-option" onClick={() => handleSelect(gif.url, gif.title)}>
                <img src={gif.preview || gif.url} alt="" loading="lazy" />
              </div>
            ))
          ) : (
            <div className="emote-empty">Search for GIFs above</div>
          )
        ) : currentEmotes.length > 0 ? (
          currentEmotes.map((emote) => (
            <div key={emote.id} className="emote-option" onClick={() => handleSelect(emote.url, emote.code)} title={emote.code}>
              <img src={emote.url} alt={emote.code} loading="lazy" />
            </div>
          ))
        ) : (
          <div className="emote-empty">No emotes available</div>
        )}
      </div>
    </div>
  );
}

function HeroBanner() {
  return (
    <div className="hero-banner">
      <div className="hero-inner">
        <div>
          <h2>Discover & Curate the Best Twitch Clips</h2>
          <p>Swipe, like, and send clips to the upload queue — discover viral moments faster.</p>
        </div>
        <div>
          <button className="btn-primary" onClick={() => { const el = document.getElementById('card-stack'); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }}>Start Swiping</button>
        </div>
      </div>
    </div>
  );
}

function AuthModal({ isOpen, onClose, onLogin }: { isOpen: boolean; onClose: () => void; onLogin: (token: string, user: User) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    // basic client-side validation
    if (!email || !password || (!isLogin && !username)) {
      setError('Please fill in all required fields');
      setLoading(false);
      return;
    }

    try {
      if (isLogin) {
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
      const msg = err?.detail || err?.message || JSON.stringify(err) || 'Authentication failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} aria-modal="true" role="dialog">
      <div className="auth-modal" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <input
              aria-label="Username"
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
          )}
          <input
            aria-label="Email"
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <div style={{ position: 'relative' }}>
            <input
              aria-label="Password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <button type="button" onClick={() => setShowPassword(s => !s)} style={{ position: 'absolute', right: 10, top: 10, background: 'none', border: 'none', color: '#8b5cf6', cursor: 'pointer' }} aria-label="Toggle password visibility">
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button type="submit" disabled={loading} aria-busy={loading}>
            {loading ? (
              <>
                <span className="video-loading active" style={{ width: 18, height: 18, borderWidth: 2, marginRight: 8 }}></span>
                Sending...
              </>
            ) : (isLogin ? 'Login' : 'Sign Up')}
          </button>
        </form>
        <p className="auth-switch">
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <button type="button" onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? 'Sign Up' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
}


function App() {
  const [activeTab, setActiveTab] = useState<Tab>('swipe');
  const [clips, setClips] = useState<Clip[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [categories, setCategories] = useState<string[]>(['My Streamers']);
  const [currentCategory, setCurrentCategory] = useState('My Streamers');
  const [loading, setLoading] = useState(true);
  const [leaderboard, setLeaderboard] = useState<LeaderboardClip[]>([]);
  const [prevLeaderboard, setPrevLeaderboard] = useState<Map<string, number>>(new Map());
  const [adminQueue, setAdminQueue] = useState<AdminClip[]>([]);
  const [aiChatMessages, setAiChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [hoveredClipId, setHoveredClipId] = useState<string | null>(null);
  const [hoveredClipVideoUrl, setHoveredClipVideoUrl] = useState<string | null>(null);
  const [selectedClipForAi, _setSelectedClipForAi] = useState<AdminClip | null>(null);
  const hoverVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const [showComments, setShowComments] = useState(false);
  const [activeCommentClip, setActiveCommentClip] = useState<{ id: string; title: string } | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [theaterVideo, setTheaterVideo] = useState<{ clipId: string; src: string } | null>(null);
  const [theaterLoading, setTheaterLoading] = useState(false);
  const [rejectHighlight, setRejectHighlight] = useState(false);
  const [acceptHighlight, setAcceptHighlight] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [leavingDirection, setLeavingDirection] = useState<'left' | 'right' | null>(null); // NEW: for exit animation
  const [showEmotePicker, setShowEmotePicker] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [userSubscription, setUserSubscription] = useState<'free' | 'trial' | 'pro'>('free');

  const cardRef = useRef<HTMLDivElement>(null);
  const theaterVideoRef = useRef<HTMLVideoElement>(null);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const currentX = useRef(0);
  const isSwiping = useRef(false);
  const commentInputRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.getMe()
        .then(userData => {
          setUser(userData);
        })
        .catch(() => {
          localStorage.removeItem('token');
        });
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get('twitch_linked') === 'true') {
      window.history.replaceState({}, '', window.location.pathname);
      api.getMe()
        .then(userData => setUser(userData))
        .catch(() => {});
    }
  }, []);

  // Debug: Log when selectedClipForAi changes
  useEffect(() => {
    if (selectedClipForAi) {
      console.log('✅ selectedClipForAi SET:', selectedClipForAi.title);
    } else {
      console.log('❌ selectedClipForAi is NULL (no clip selected for AI editor)');
    }
  }, [selectedClipForAi]);

  useEffect(() => {
    if (activeTab === 'leaderboard') {
      loadLeaderboard();
      
      wsRef.current = createLeaderboardSocket((updatedClips) => {
        const newLeaderboard = updatedClips.slice(0, 10);
        
        const prevPositions = new Map<string, number>();
        leaderboard.forEach((clip, idx) => {
          prevPositions.set(clip.id, idx);
        });
        setPrevLeaderboard(prevPositions);
        
        setLeaderboard(newLeaderboard);
        setWsConnected(true);
      });

      return () => {
        wsRef.current?.close();
        setWsConnected(false);
      };
    } else {
      wsRef.current?.close();
      setWsConnected(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    if (activeTab === 'swipe' && currentCategory) {
      if (!currentCategory) return;
      setLoading(true);
      api.getClips(currentCategory).then((data) => {
        const seenIds = getSeenClipIds();
        const filteredClips = data.clips.filter(c => !seenIds.has(c.id));
        setClips(filteredClips);
        setCurrentIndex(0);
      }).catch((err) => {
        console.error('Failed to load clips:', err);
      }).finally(() => {
        setLoading(false);
      });
    } else if (activeTab === 'admin') {
      loadAdminQueue();
    }
  }, [activeTab, currentCategory]);

  useEffect(() => {
    if (theaterVideo && theaterVideoRef.current) {
      theaterVideoRef.current.volume = 0.05;
    }
  }, [theaterVideo]);

  const loadCategories = async () => {
    try {
      const data = await api.getCategories();
      setCategories(['My Streamers', ...data.categories]);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadLeaderboard = async () => {
    try {
      const data = await api.getLeaderboard();
      setLeaderboard(data.slice(0, 10));
    } catch (err) {
      console.error('Failed to load leaderboard:', err);
    }
  };

  const loadAdminQueue = async () => {
    try {
      const data = await api.getAcceptedClips();
      setAdminQueue(data);
    } catch (err) {
      console.error('Failed to load admin queue:', err);
    }
  };

  const handleAiChatSubmit = async () => {
    console.log('🔵 Send Button Clicked');
    console.log('State Debug:', {
      aiInput: aiInput.trim(),
      aiInputTrimmed: !!aiInput.trim(),
      selectedClipForAi: selectedClipForAi,
      aiLoading: aiLoading,
    });

    if (!aiInput.trim() || !selectedClipForAi || aiLoading) {
      console.log('❌ Send blocked - Reasons:');
      if (!aiInput.trim()) console.log('   - aiInput is empty');
      if (!selectedClipForAi) console.log('   - selectedClipForAi is null (no clip selected!)');
      if (aiLoading) console.log('   - aiLoading is true (request in progress)');
      return;
    }

    console.log('✅ Send proceeding...');
    const userMsg = aiInput.trim();
    setAiInput('');
    setAiLoading(true);

    // Add user message to chat
    setAiChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);

    try {
      const response = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clip_title: selectedClipForAi.title,
          clip_channel: selectedClipForAi.channel,
          user_message: userMsg,
          conversation_history: aiChatMessages,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setAiChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (error) {
      console.error('AI chat error:', error);
      setAiChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I couldn\'t process your request. Please try again.'
      }]);
    } finally {
      setAiLoading(false);
    }
  };

  const loadComments = async (clipId: string) => {
    try {
      const data = await api.getComments(clipId);
      setComments(data);
    } catch (err) {
      console.error('Failed to load comments:', err);
    }
  };

  const stopAllVideos = useCallback(() => {
    const videos = document.querySelectorAll('.clip-preview video');
    videos.forEach(video => {
      (video as HTMLVideoElement).pause();
      (video as HTMLVideoElement).currentTime = 0;
    });
  }, []);

  const handleSwipe = useCallback(async (direction: 'left' | 'right') => {
    if (isSwiping.current) return;
    const currentClip = clips[currentIndex];
    if (!currentClip) return;

    isSwiping.current = true;
    setLeavingDirection(direction); // trigger exit animation
    stopAllVideos();

    // Delay actual removal until animation completes
    setTimeout(() => {
      addSeenClipId(currentClip.id);

      const nextClip = clips[currentIndex + 1];
      if (nextClip && !videoUrlCache[nextClip.id]) {
        api.getVideoUrl(nextClip.id).then((data) => {
          if (data.video_url) videoUrlCache[nextClip.id] = data.video_url;
        }).catch(() => {});
      }

      if (direction === 'right') {
        if (user) {
          api.likeClip(currentClip.id).catch(() => {});
        } else {
          api.legacyLikeClip(currentClip.id).catch(() => {});
        }
      } else {
        if (user) {
          api.dislikeClip(currentClip.id).catch(() => {});
        } else {
          api.legacyDislikeClip(currentClip.id).catch(() => {});
        }
      }

      const newIndex = currentIndex + 1;
      if (newIndex >= clips.length - 2) {
        api.getClips(currentCategory).then((data) => {
          const seenIds = getSeenClipIds();
          const newClips = data.clips.filter(c => !seenIds.has(c.id));
          if (newClips.length > 0) {
            setClips(prev => [...prev.filter(c => !seenIds.has(c.id)), ...newClips]);
          }
        }).catch(() => {});
      }

      setCurrentIndex(newIndex);
      setLeavingDirection(null);
      setSwipeDirection(null);
      isSwiping.current = false;
    }, 320); // match CSS transition duration
  }, [clips, currentIndex, stopAllVideos, user, currentCategory]);

  const handleMouseDown = (e: React.MouseEvent | React.TouchEvent) => {
    if (isSwiping.current) return;
    const target = e.target as HTMLElement;
    if (target.closest('.volume-control, .fullscreen-btn, .play-pause-btn, .progress-container, .clip-info, button')) return;

    isDragging.current = true;
    startX.current = 'touches' in e ? e.touches[0].clientX : e.clientX;
    currentX.current = startX.current;
    cardRef.current?.classList.add('dragging');
    stopAllVideos();
  };

  const handleMouseMove = useCallback((e: MouseEvent | TouchEvent) => {
    if (!isDragging.current || !cardRef.current) return;
    if ('preventDefault' in e) e.preventDefault();

    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    currentX.current = clientX;

    const deltaX = clientX - startX.current;
    cardRef.current.style.transform = `translate(${deltaX}px, 0) rotate(${deltaX * 0.03}deg)`;

    const swipeThreshold = 50;

    if (deltaX < -swipeThreshold) {
      setRejectHighlight(true);
      setAcceptHighlight(false);
      const nopeHint = cardRef.current.querySelector('.swipe-hint.left') as HTMLElement;
      if (nopeHint) {
        const progress = Math.min(1.5, (Math.abs(deltaX) - swipeThreshold) / 100);
        nopeHint.style.transform = `scale(${0.5 + progress * 0.7})`;
        nopeHint.style.opacity = String(progress);
      }
    } else if (deltaX > swipeThreshold) {
      setAcceptHighlight(true);
      setRejectHighlight(false);
      const likeHint = cardRef.current.querySelector('.swipe-hint.right') as HTMLElement;
      if (likeHint) {
        const progress = Math.min(1.5, (deltaX - swipeThreshold) / 100);
        likeHint.style.transform = `scale(${0.5 + progress * 0.7})`;
        likeHint.style.opacity = String(progress);
      }
    } else {
      setRejectHighlight(false);
      setAcceptHighlight(false);
      const nopeHint = cardRef.current.querySelector('.swipe-hint.left') as HTMLElement;
      const likeHint = cardRef.current.querySelector('.swipe-hint.right') as HTMLElement;
      if (nopeHint) { nopeHint.style.opacity = '0'; nopeHint.style.transform = 'scale(0.5)'; }
      if (likeHint) { likeHint.style.opacity = '0'; likeHint.style.transform = 'scale(0.5)'; }
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!isDragging.current || !cardRef.current) return;
    isDragging.current = false;
    cardRef.current.classList.remove('dragging');

    const deltaX = currentX.current - startX.current;
    setRejectHighlight(false);
    setAcceptHighlight(false);

    const nopeHint = cardRef.current.querySelector('.swipe-hint.left') as HTMLElement;
    const likeHint = cardRef.current.querySelector('.swipe-hint.right') as HTMLElement;
    if (nopeHint) { nopeHint.style.opacity = '0'; nopeHint.style.transform = 'scale(0.5)'; }
    if (likeHint) { likeHint.style.opacity = '0'; likeHint.style.transform = 'scale(0.5)'; }

    if (Math.abs(deltaX) > 100) {
      cardRef.current.classList.remove('top-card');
      handleSwipe(deltaX > 0 ? 'right' : 'left');
    } else {
      cardRef.current.style.transform = '';
    }
  }, [handleSwipe]);

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchmove', handleMouseMove, { passive: false });
    document.addEventListener('touchend', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchmove', handleMouseMove);
      document.removeEventListener('touchend', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const openComments = (clipId: string, title: string) => {
    setActiveCommentClip({ id: clipId, title });
    loadComments(clipId);
    setShowComments(true);
  };

  const closeComments = () => {
    setShowComments(false);
    setActiveCommentClip(null);
  };

  const postComment = async () => {
    if (!activeCommentClip || !commentInputRef.current) return;
    const text = commentInputRef.current.innerHTML.trim();
    if (!text || text === '<br>') return;

    commentInputRef.current.innerHTML = '';
    try {
      await api.postComment(activeCommentClip.id, text);
      loadComments(activeCommentClip.id);
    } catch (err) {
      alert('Failed to post comment');
    }
  };

  const openTheaterMode = async (clipId: string) => {
    setTheaterLoading(true);
    try {
      const data = await api.getVideoUrl(clipId);
      if (data.video_url) {
        setTheaterVideo({ clipId, src: data.video_url });
      }
    } catch (err) {
      alert('Could not load full video.');
    } finally {
      setTheaterLoading(false);
    }
  };

  const closeTheaterMode = () => {
    if (theaterVideoRef.current) {
      theaterVideoRef.current.pause();
    }
    setTheaterVideo(null);
  };

  const formatViews = (views: number) => {
    if (views >= 1000) return `${(views / 1000).toFixed(1)}K`;
    return views.toString();
  };

  const handleCategoryChange = async (cat: string, e: React.MouseEvent<HTMLButtonElement>) => {
    if (cat === currentCategory) return;
    
    document.querySelectorAll('.cat-pill').forEach(el => el.classList.remove('active'));
    e.currentTarget.classList.add('active');
    
    stopAllVideos();
    setClips([]);
    setCurrentIndex(0);
    setCurrentCategory(cat);
  };

  const handleAddToQueue = async (clipId: string) => {
    await api.addToQueue(clipId);
    loadAdminQueue();
    alert('✅ Sent to Admin Upload Queue!');
  };

  // const handleRemoveFromQueue = async (clipId: string) => {
  //   await api.removeFromQueue(clipId);
  //   loadAdminQueue();
  // };

  const handleLogin = (_token: string, userData: User) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const visibleClips = useMemo(() => clips.slice(currentIndex, Math.min(currentIndex + 3, clips.length)), [clips, currentIndex]);

  return (
    <>
      <header>
        <h1>Clip<span className="logo-accent">der</span> Pro</h1>
        <nav className="nav-tabs">
          <button className={`tab-btn ${activeTab === 'swipe' ? 'active' : ''}`} onClick={() => { setActiveTab('swipe'); closeComments(); stopAllVideos(); }}>Swipe & Vote</button>
          <button className={`tab-btn ${activeTab === 'leaderboard' ? 'active' : ''}`} onClick={() => { setActiveTab('leaderboard'); closeComments(); loadLeaderboard(); stopAllVideos(); }}>
            Leaderboard {wsConnected && <span className="ws-indicator"></span>}
          </button>
          <button className={`tab-btn ${activeTab === 'ai-editor' ? 'active' : ''}`} onClick={() => { setActiveTab('ai-editor'); closeComments(); loadAdminQueue(); stopAllVideos(); }}>🚀 AI Editor</button>
          <button className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => { setActiveTab('profile'); closeComments(); stopAllVideos(); }}>Profile</button>
        </nav>
        <div className="auth-section">
          {user ? (
            <div className="user-menu">
              <span>{user.username}</span>
              {user.twitch_username && <span className="twitch-badge">📺 {user.twitch_username}</span>}
              <button onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <button className="auth-btn" onClick={() => setShowAuthModal(true)}>Login</button>
          )}
        </div>
      </header>

      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} onLogin={handleLogin} />

      <div className="app-container">
        <div id="swipe" className={`view-section ${activeTab === 'swipe' ? 'active' : ''}`}>
          <div style={{ width: '100%', padding: '0 5%' }}>
            <HeroBanner />
          </div>
          <div className="category-menu">
            {categories.map((cat) => (
              <button key={cat} className={`cat-pill ${currentCategory === cat ? 'active' : ''}`} onClick={(e) => handleCategoryChange(cat, e)}>
                {cat}
              </button>
            ))}
          </div>

          <div className="swipe-container">
            <div className="action-buttons">
              <button className={`btn-side btn-reject ${rejectHighlight ? 'highlight' : ''}`} onClick={() => handleSwipe('left')} title="Skip">
                <svg viewBox="0 0 120 160" fill="none">
                  <g opacity="0.15"><circle cx="25" cy="80" r="18" fill="currentColor"/><circle cx="60" cy="65" r="8" fill="currentColor"/><circle cx="45" cy="100" r="5" fill="currentColor"/><circle cx="80" cy="75" r="3" fill="currentColor"/><circle cx="35" cy="55" r="4" fill="currentColor"/><circle cx="55" cy="110" r="3" fill="currentColor"/></g>
                  <path d="M95 78 Q88 78 75 78 L45 78" stroke="currentColor" strokeWidth="14" strokeLinecap="round" opacity="0.9"/>
                  <path d="M55 55 L25 80 L55 105" stroke="currentColor" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                  <path d="M30 95 Q30 115 32 125" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.5"/>
                  <path d="M50 105 Q49 118 50 122" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.4"/>
                  <path d="M70 83 Q70 95 71 100" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3"/>
                  <text x="60" y="42" fontFamily="'Arial Black', Impact, sans-serif" fontSize="20" fontWeight="900" fill="currentColor" opacity="0.7" letterSpacing="3" transform="rotate(-8, 60, 42)">SKIP</text>
                </svg>
              </button>
              <button className={`btn-side btn-accept ${acceptHighlight ? 'highlight' : ''}`} onClick={() => handleSwipe('right')} title="Like">
                <svg viewBox="0 0 120 160" fill="none">
                  <g opacity="0.15"><circle cx="95" cy="80" r="18" fill="currentColor"/><circle cx="60" cy="65" r="8" fill="currentColor"/><circle cx="75" cy="100" r="5" fill="currentColor"/><circle cx="40" cy="75" r="3" fill="currentColor"/><circle cx="85" cy="55" r="4" fill="currentColor"/><circle cx="65" cy="110" r="3" fill="currentColor"/></g>
                  <path d="M25 78 Q32 78 45 78 L75 78" stroke="currentColor" strokeWidth="14" strokeLinecap="round" opacity="0.9"/>
                  <path d="M65 55 L95 80 L65 105" stroke="currentColor" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                  <path d="M90 95 Q90 115 88 125" stroke="currentColor" strokeWidth="3" strokeLinecap="round" opacity="0.5"/>
                  <path d="M70 105 Q71 118 70 122" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.4"/>
                  <path d="M50 83 Q50 95 49 100" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.3"/>
                  <text x="60" y="42" fontFamily="'Arial Black', Impact, sans-serif" fontSize="20" fontWeight="900" fill="currentColor" opacity="0.7" letterSpacing="3" textAnchor="middle" transform="rotate(8, 60, 42)">LIKE</text>
                </svg>
              </button>
            </div>

            <div id="card-stack">
              {loading ? (
                <div id="loading">
                  <div className="video-loading active" style={{ position: 'relative', top: 'auto', left: 'auto', transform: 'none' }}></div>
                  <p style={{ marginTop: '16px', fontWeight: 600, color: '#888' }}>Loading...</p>
                </div>
              ) : currentIndex >= clips.length ? (
                <div className="empty-msg">
                  <h2>All Caught Up</h2>
                  <p style={{ marginTop: '10px' }}>No more clips to vote on</p>
                </div>
              ) : (
                visibleClips.map((clip, idx) => {
                  // card-swipe exit animation: if top card and leavingDirection, animate out
                  let cardStyle: React.CSSProperties = {
                    zIndex: 100 - idx,
                    pointerEvents: idx === 0 ? 'auto' : 'none',
                    transition: 'transform 0.32s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.28s',
                  };
                  if (idx === 0 && leavingDirection) {
                    cardStyle = {
                      ...cardStyle,
                      transform: `translate(${leavingDirection === 'right' ? '150%' : '-150%'}, -100px) rotate(${leavingDirection === 'right' ? 32 : -32}deg) scale(0.95)`,
                      opacity: 0,
                    };
                  } else if (idx === 0 && swipeDirection) {
                    // fallback for button-triggered swipe
                    cardStyle = {
                      ...cardStyle,
                      transform: `translate(${swipeDirection === 'right' ? '150%' : '-150%'}, -100px) rotate(${swipeDirection === 'right' ? 30 : -30}deg) scale(0.95)`,
                      opacity: 0,
                    };
                  } else if (idx > 0) {
                    cardStyle = {
                      ...cardStyle,
                      transform: `scale(${1 - idx * 0.03}) translateY(${idx * 10}px)`,
                      opacity: 1 - idx * 0.12,
                    };
                  }
                  return (
                    <div
                      key={clip.id}
                      ref={idx === 0 ? cardRef : null}
                      className={`clip-card ${idx === 0 ? 'top-card' : ''}`}
                      style={cardStyle}
                      onMouseDown={idx === 0 ? handleMouseDown : undefined}
                      onTouchStart={idx === 0 ? handleMouseDown : undefined}
                    >
                      <ClipPreview
                        clip={clip}
                        onOpenTheater={() => openTheaterMode(clip.id)}
                        isPreload={idx !== 0}
                      >
                        <div className="clip-info" style={{ pointerEvents: 'none' }}>
                          <div className="clip-title">{clip.title}</div>
                          <div className="creator">{clip.creator_name} • {clip.channel}</div>
                          <div className="clip-meta">
                            <div>
                              <span>👁 {formatViews(clip.view_count)}</span>
                              <span style={{ marginLeft: '8px' }}>⏱ {Math.floor(clip.duration)}s</span>
                            </div>
                            <div className="social-counters">
                              <div className="social-badge">♥ <span>{clip.local_likes}</span></div>
                              <button className="social-btn" onClick={(e) => { e.stopPropagation(); openComments(clip.id, clip.title); }}>💬 <span>{clip.comment_count}</span></button>
                            </div>
                          </div>
                        </div>
                      </ClipPreview>
                      <div className="swipe-hint left" style={{ opacity: 0 }}>
                        <div className="aura-strings"></div>
                        <div className="hint-text-main">NOPE</div>
                        <div className="hint-text-bubbly">I dare you!</div>
                      </div>
                      <div className="swipe-hint right" style={{ opacity: 0 }}>
                        <div className="aura-strings"></div>
                        <div className="hint-text-main">LIKE</div>
                        <div className="hint-text-bubbly">Shiny! ✨</div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        <div id="leaderboard" className={`view-section ${activeTab === 'leaderboard' ? 'active' : ''}`}>
          <div className="list-container">
            <h2 className="section-title">🏆 Top 10 Viral Clips</h2>
            <div className="section-subtitle">
              {wsConnected ? (
                <span className="live-indicator">🔴 LIVE</span>
              ) : (
                <span>Live updates enabled when you're on this tab</span>
              )}
              {' '}- Hover to preview, or click expand for Theater Mode!
            </div>

            {leaderboard.length === 0 ? (
              <div className="empty-msg">No clips have been liked yet!<br />Go swipe right to build the leaderboard.</div>
            ) : (
              <div className="leaderboard-list">
                {leaderboard.map((clip, index) => {
                  const prevIndex = prevLeaderboard.get(clip.id);
                  const isMovingUp = prevIndex !== undefined && prevIndex > index;
                  const isMovingDown = prevIndex !== undefined && prevIndex < index;
                  const isNew = prevIndex === undefined;
                  
                  return (
                    <div 
                      key={clip.id} 
                      className={`list-item ${isMovingUp ? 'moving-up' : ''} ${isMovingDown ? 'moving-down' : ''} ${isNew ? 'new-entry' : ''}`}
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      <div className={`rank-badge rank-${index + 1}`}>#{index + 1}</div>
                      <div className="thumb-wrapper">
                        <MiniThumb clip={clip} onOpenTheater={() => openTheaterMode(clip.id)} isHighlighted={isMovingUp || isMovingDown || isNew} />
                      </div>
                      <div className="item-details">
                        <div className="item-title">{clip.title}</div>
                        <div className="item-stats">
                          <span className="likes-count">♥ {clip.local_likes} Likes</span>
                          <button className="social-btn" style={{ padding: '2px 8px', fontSize: '1em', background: 'transparent', border: '1px solid rgba(255,255,255,0.1)' }} onClick={() => openComments(clip.id, clip.title)}>💬 {clip.comment_count}</button>
                          <span>👁 {formatViews(clip.view_count)} views</span>
                          <span>{clip.channel}</span>
                        </div>
                      </div>
                      <button className="btn-small btn-outline" onClick={() => handleAddToQueue(clip.id)}>+ Send to Queue</button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div id="ai-editor" className={`view-section ${activeTab === 'ai-editor' ? 'active' : ''}`} style={{ display: 'flex', flexDirection: 'column', padding: '20px', overflow: 'auto', alignItems: 'center' }}>
          
          {userSubscription === 'free' ? (
            // PRICING SECTION FOR FREE USERS
            <div style={{ width: '100%', maxWidth: '1400px' }}>
              <div className="pricing-hero">
                <h2>🚀 AI Editor Pro</h2>
                <p>Transform your clips with AI-powered editing suggestions. Get pro-level edits in seconds, not hours.</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', alignItems: 'start', marginBottom: '40px' }}>
                {/* DEMO VIDEO */}
                <div>
                  <DemoVideo />
                </div>

                {/* PRICING CARDS ON RIGHT */}
                <div>
              <div className="pricing-cards">
            {/* FREE TRIAL CARD */}
            <div className="pricing-card">
              <div className="card-header">
                <div className="card-title">Free Trial</div>
                <div>
                  <div className="card-price">Free</div>
                </div>
              </div>
              <p className="card-description">Get started with limited AI editing credits</p>
              <div className="card-benefits">
                <div className="benefit-item">
                  <span className="benefit-icon">⭐</span>
                  <span>3 AI edits per month</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">✨</span>
                  <span>Basic editing suggestions</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">🎬</span>
                  <span>720p preview quality</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">⏱</span>
                  <span>No expiration - use anytime</span>
                </div>
              </div>
              <button 
                className="pricing-btn pricing-btn-secondary"
                onClick={() => {
                  setUserSubscription('trial');
                  setActiveTab('ai-editor');
                }}
              >
                Start Free Trial
              </button>
            </div>

            {/* MONTHLY CARD */}
            <div className="pricing-card">
              <div className="card-header">
                <div className="card-title">Pro Monthly</div>
                <div>
                  <div className="card-price">$9.99<span className="card-price-period">/mo</span></div>
                </div>
              </div>
              <p className="card-description">Perfect for serious content creators</p>
              <div className="card-benefits">
                <div className="benefit-item">
                  <span className="benefit-icon">⭐</span>
                  <span>Unlimited AI edits per month</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">✨</span>
                  <span>Advanced multi-prompt suggestions</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">🎬</span>
                  <span>1080p + HD exports</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">🎵</span>
                  <span>Music library access</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">⚙️</span>
                  <span>Priority support</span>
                </div>
              </div>
              <button 
                className="pricing-btn pricing-btn-primary"
                onClick={() => {
                  setUserSubscription('pro');
                  setActiveTab('ai-editor');
                }}
              >
                Upgrade to Pro
              </button>
            </div>

            {/* YEARLY CARD - FEATURED */}
            <div className="pricing-card featured">
              <div className="featured-badge">BEST VALUE 40% OFF</div>
              <div className="card-header">
                <div className="card-title">Pro Yearly</div>
                <div>
                  <div className="card-price">$71.88<span className="card-price-period">/yr</span></div>
                </div>
              </div>
              <p className="card-description">Save $47.88 vs monthly. Most popular choice.</p>
              <div className="card-benefits">
                <div className="benefit-item">
                  <span className="benefit-icon">⭐</span>
                  <span>All Pro features included</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">💎</span>
                  <span>Unlimited everything</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">🎬</span>
                  <span>4K export capabilities</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">🤖</span>
                  <span>Early access to new AI features</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">👥</span>
                  <span>16 team member slots</span>
                </div>
                <div className="benefit-item">
                  <span className="benefit-icon">🚀</span>
                  <span>VIP priority support (24/7)</span>
                </div>
              </div>
              <button 
                className="pricing-btn pricing-btn-primary"
                onClick={() => {
                  setUserSubscription('pro');
                  setActiveTab('ai-editor');
                }}
              >
                Get Yearly Deal
              </button>
            </div>
          </div>
                </div>
              </div>

          {/* FOOTER CTA */}
          <div className="pricing-footer">
            <p>🎁 <span className="limited-offer">Limited time: First month 50% off any plan!</span></p>
            <p style={{ fontSize: '0.8em', color: '#666' }}>Cancel anytime. No hidden fees. Start your free trial now.</p>
          </div>
            </div>
          ) : (
            // AI CHAT INTERFACE FOR PRO/TRIAL USERS
            <div style={{ width: '100%', height: '100%', display: 'flex', gap: '16px', position: 'relative', padding: '20px' }}>
              {/* CHAT SECTION - LEFT SIDE */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
                <video
                  src="/videos/maya.mp4"
                  autoPlay
                  loop
                  muted
                  playsInline
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    opacity: 0.15,
                    zIndex: 0,
                    pointerEvents: 'none',
                    borderRadius: '14px'
                  }}
                />
                <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <h2 style={{ marginBottom: '20px', textAlign: 'center' }}>✨ AI Editor Playground</h2>
                  
                  {/* Chat Panel */}
                  <div 
                    style={{ 
                      background: 'rgba(147, 51, 234, 0.1)', 
                      borderRadius: '14px', 
                      border: '1px solid rgba(147, 51, 234, 0.2)', 
                      padding: '20px', 
                      display: 'flex', 
                      flexDirection: 'column', 
                      gap: '16px',
                      flex: 1,
                      minHeight: 0
                    }}
                    onDragOver={(e) => {
                      e.preventDefault();
                      e.currentTarget.style.background = 'rgba(147, 51, 234, 0.2)';
                      e.currentTarget.style.borderColor = 'rgba(147, 51, 234, 0.6)';
                    }}
                    onDragLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(147, 51, 234, 0.1)';
                      e.currentTarget.style.borderColor = 'rgba(147, 51, 234, 0.2)';
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.currentTarget.style.background = 'rgba(147, 51, 234, 0.1)';
                      e.currentTarget.style.borderColor = 'rgba(147, 51, 234, 0.2)';
                      
                      const clipId = e.dataTransfer?.getData('clipId');
                      const clipTitle = e.dataTransfer?.getData('clipTitle');
                      const clipDataStr = e.dataTransfer?.getData('clipData');
                      
                      if (clipId) {
                        // Parse the clip data and set it for AI editor
                        const clip = clipDataStr ? JSON.parse(clipDataStr) : null;
                        if (clip) {
                          _setSelectedClipForAi(clip);
                          console.log('✅ Clip dropped in AI editor, selectedClipForAi SET:', clip);
                        } else {
                          console.log('❌ Could not parse clip data from drop event');
                        }
                        
                        // Add user message (clip dropped)
                        setAiChatMessages(prev => [...prev, { role: 'user', content: `📎 ${clipTitle} (dropped for editing)` }]);
                        // Add AI response
                        setTimeout(() => {
                          setAiChatMessages(prev => [...prev, { role: 'assistant', content: 'How can I make you money today? ;)' }]);
                        }, 800);
                      }
                    }}
                  >
                    <h3 style={{ color: '#d8b4fe' }}>🤖 Your AI Coach</h3>
                    
                    <div style={{ flex: 1, background: 'rgba(0, 0, 0, 0.2)', borderRadius: '8px', padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {aiChatMessages.length === 0 ? (
                        <div style={{ textAlign: 'center', color: 'rgba(255, 255, 255, 0.5)', margin: 'auto', fontSize: '0.95em' }}>
                          💡 Drag a clip from the right to start editing!
                        </div>
                      ) : (
                        aiChatMessages.map((msg, idx) => (
                          <div key={idx} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                            <div style={{ background: msg.role === 'user' ? 'linear-gradient(135deg, #9333ea, #ec4899)' : 'rgba(59, 130, 246, 0.2)', color: 'white', padding: '12px 14px', borderRadius: '12px', maxWidth: '75%', wordWrap: 'break-word' }}>
                              {msg.content}
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" 
                        value={aiInput}
                        onChange={(e) => setAiInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAiChatSubmit()}
                        placeholder="Describe your editing vision..."
                        style={{ flex: 1, padding: '10px 14px', background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(147, 51, 234, 0.2)', borderRadius: '8px', color: 'white' }}
                      />
                      <button 
                        onClick={handleAiChatSubmit}
                        style={{ padding: '10px 16px', background: 'linear-gradient(135deg, #9333ea, #ec4899)', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer' }}
                      >
                        Send ✨
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* QUEUE SECTION - RIGHT SIDE (SEPARATE DIV) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: 'calc(100vh - 80px)', width: '320px', background: 'rgba(0, 0, 0, 0.8)', borderRadius: '14px', border: '1px solid rgba(0, 0, 0, 0.6)', padding: '16px', overflowY: 'auto', flexShrink: 0 }}>
                <h3 style={{ color: '#f472b6', margin: 0, fontSize: '0.95em' }}>📺 Queue</h3>
                
                {adminQueue.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'rgba(255, 255, 255, 0.4)', padding: '40px 10px', fontSize: '0.85em' }}>
                    <div style={{ fontSize: '2em', marginBottom: '8px' }}>📤</div>
                    <div>Send clips</div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {adminQueue.map((clip: AdminClip) => (
                      <div
                        key={clip.id}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer?.setData('clipId', clip.id);
                          e.dataTransfer?.setData('clipTitle', clip.title);
                          e.dataTransfer?.setData('clipData', JSON.stringify(clip));
                          console.log('🎬 Dragged clip:', clip);
                        }}
                            style={{
                              position: 'relative',
                              borderRadius: '10px',
                              overflow: 'hidden',
                              border: '2px solid rgba(236, 72, 153, 0.4)',
                              cursor: 'grab',
                              transition: 'all 0.3s ease',
                              background: 'rgba(0, 0, 0, 0.5)',
                              height: '85px',
                              backgroundImage: `url(${clip.thumbnail_url})`,
                              backgroundSize: 'cover',
                              backgroundPosition: 'center',
                              flexShrink: 0
                            }}
                            className="clip-thumbnail-ai"
                            onMouseEnter={async (e) => {
                              (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)';
                              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(236, 72, 153, 0.8)';
                              (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px rgba(236, 72, 153, 0.3)';
                              setHoveredClipId(clip.id);
                              if (!hoveredClipVideoUrl || hoveredClipId !== clip.id) {
                                try {
                                  const data = await api.getVideoUrl(clip.id);
                                  if (data.video_url) {
                                    setHoveredClipVideoUrl(data.video_url);
                                    setTimeout(() => {
                                      if (hoverVideoRefs.current[clip.id]) {
                                        hoverVideoRefs.current[clip.id]?.play().catch(() => {});
                                      }
                                    }, 50);
                                  }
                                } catch (err) {
                                  console.error('Error fetching video:', err);
                                }
                              }
                            }}
                            onMouseLeave={(e) => {
                              (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
                              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(236, 72, 153, 0.3)';
                              (e.currentTarget as HTMLElement).style.boxShadow = 'none';
                              setHoveredClipId(null);
                              if (hoverVideoRefs.current[clip.id]) {
                                hoverVideoRefs.current[clip.id]?.pause();
                              }
                            }}
                          >
                            {/* Thumbnail with title overlay */}
                            <div style={{ width: '100%', height: '100%', background: 'linear-gradient(to bottom, transparent, rgba(0, 0, 0, 0.8))', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', position: 'relative', padding: '6px' }}>
                              <div style={{ textAlign: 'center', fontSize: '0.65em', color: 'rgba(255, 255, 255, 0.9)', lineHeight: '1.1', maxHeight: '100%', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', fontWeight: 500 }}>
                                {clip.title}
                              </div>
                            </div>

                            {/* Hover video preview */}
                            {hoveredClipId === clip.id && (
                              <div style={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                width: '100%',
                                height: '100%',
                                background: 'rgba(0, 0, 0, 0.95)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '10px',
                                zIndex: 10,
                                flexDirection: 'column'
                              }}>
                                {hoveredClipVideoUrl ? (
                                  <>
                                    <video 
                                      ref={(el) => { if (el) hoverVideoRefs.current[clip.id] = el; }}
                                      src={hoveredClipVideoUrl}
                                      style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '10px' }}
                                      muted
                                      loop
                                      autoPlay
                                    />
                                    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.8), transparent)', padding: '8px 6px', color: 'white' }}>
                                      <div style={{ fontSize: '0.6em', lineHeight: '1.1', maxHeight: '30px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {clip.title}
                                      </div>
                                    </div>
                                  </>
                                ) : (
                                  <div style={{ textAlign: 'center', color: 'rgba(255, 255, 255, 0.6)' }}>
                                    <div style={{ fontSize: '1.2em', marginBottom: '2px' }}>⏳</div>
                                    <div style={{ fontSize: '0.6em' }}>Loading...</div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
            </div>
          )}
        </div>

        <div id="profile" className={`view-section ${activeTab === 'profile' ? 'active' : ''}`}>
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
                      <span>Connected as: <strong>@{user.twitch_username}</strong></span>
                      <button className="btn-small btn-outline" onClick={() => api.unlinkTwitch().then(() => window.location.reload())}>Unlink</button>
                    </div>
                  ) : (
                    <button className="btn-small btn-primary" onClick={async () => {
                      const { authorization_url } = await api.getTwitchLoginUrl();
                      const popup = window.open(authorization_url, 'Twitch OAuth', 'width=600,height=700');
                      
                      const handleMessage = (event: MessageEvent) => {
                        if (event.data?.type === 'twitch_linked') {
                          window.removeEventListener('message', handleMessage);
                          api.getMe().then(setUser);
                          popup?.close();
                        }
                      };
                      window.addEventListener('message', handleMessage);
                    }}>Connect Twitch Account</button>
                  )}
                </div>

                <div className="following-section">
                  <h4>⭐ My Streamers</h4>
                  <p className="section-subtitle">Streamers you want to see in your swipe feed</p>
                  <p className="hint-text">Connect your Twitch account above to sync your follows automatically!</p>
                </div>
              </div>
            ) : (
              <div className="auth-prompt">
                <p>Please login to access your profile</p>
                <button className="btn-primary" onClick={() => setShowAuthModal(true)}>Login</button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div id="theater-modal" className={theaterVideo ? 'show' : ''} style={{ display: theaterVideo ? 'flex' : 'none' }}>
        <div className="theater-backdrop" onClick={closeTheaterMode}></div>
        <button className="theater-close" onClick={closeTheaterMode}>✕</button>
        <div className="theater-content">
          <div className="theater-video-wrapper">
            {theaterLoading ? (
              <div style={{ width: '100%', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', borderRadius: '16px' }}>
                <div className="video-loading active"></div>
              </div>
            ) : theaterVideo && <video id="theater-video" ref={theaterVideoRef} controls autoPlay src={theaterVideo.src}></video>}
          </div>
        </div>
      </div>

      <div id="comments-sidebar" className={showComments ? 'show' : ''}>
        <div className="comments-header">
          <span>{activeCommentClip?.title || 'Comments'}</span>
          <button className="close-comments" onClick={closeComments}>✕</button>
        </div>
        <div className="comments-list">
          {comments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#666' }}>No comments yet. Be the first!</div>
          ) : (
            comments.map((c) => (
              <div key={c.timestamp} className="comment-item">
                <div className="comment-user">{c.user}</div>
                <div className="comment-text" dangerouslySetInnerHTML={{ __html: c.text }} />
              </div>
            ))
          )}
        </div>
        <div className="comments-input-wrapper">
          {showEmotePicker && (
            <EmotePicker
              onSelect={(url, code) => {
                if (commentInputRef.current) {
                  const img = document.createElement('img');
                  img.src = url;
                  img.className = 'chat-emote';
                  img.alt = code;
                  commentInputRef.current.appendChild(img);
                  commentInputRef.current.appendChild(document.createTextNode('\u00A0'));
                  commentInputRef.current.focus();
                }
              }}
              onClose={() => setShowEmotePicker(false)}
            />
          )}
          <div
            ref={commentInputRef}
            className="comment-input"
            contentEditable
            suppressContentEditableWarning
            data-placeholder="Add a comment..."
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                postComment();
              }
            }}
          ></div>
          <button className="emote-toggle-btn" onClick={() => setShowEmotePicker(!showEmotePicker)}>☺</button>
          <button className="send-btn" onClick={postComment}>Send</button>
        </div>
      </div>
    </>
  );
}

export default App;
