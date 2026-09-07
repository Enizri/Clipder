import React, { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { isDemoMode } from '../demo/demoClips';
import { videoUrlCache } from '../utils/videoCache';
import type { Clip } from '../types';

interface ClipPreviewProps {
  clip: Clip;
  onOpenTheater: () => void;
  isPreload?: boolean;
  children?: React.ReactNode;
}

export const ClipPreview = React.memo(function ClipPreview({
  clip,
  onOpenTheater,
  isPreload,
  children,
}: ClipPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(5);
  const [progress, setProgress] = useState(0);
  const [isHovering, setIsHovering] = useState(false);

  const fetchVideoUrl = useCallback(() => {
    if (videoSrc || isDemoMode()) return;
    if (videoUrlCache[clip.id]) {
      setVideoSrc(videoUrlCache[clip.id]);
      return;
    }
    setIsLoading(true);
    api
      .getVideoUrl(clip.id)
      .then((data) => {
        if (data.video_url) {
          videoUrlCache[clip.id] = data.video_url;
          setVideoSrc(data.video_url);
        }
      })
      .catch(() => {
        // Video URL fetch failed — card stays with thumbnail
      })
      .finally(() => setIsLoading(false));
  }, [clip.id, videoSrc]);

  // Seed from cache if preloading (next card in stack)
  useEffect(() => {
    if (isPreload && !videoSrc && videoUrlCache[clip.id]) {
      setVideoSrc(videoUrlCache[clip.id]);
    }
  }, [isPreload, videoSrc, clip.id]);

  // Trigger fetch when hovering or preloading
  useEffect(() => {
    if (isHovering || isPreload) fetchVideoUrl();
  }, [isHovering, isPreload, fetchVideoUrl]);

  // Auto-play once the src lands and we're still hovering
  useEffect(() => {
    if (!videoSrc || !isHovering) return;
    const video = videoRef.current;
    if (!video) return;
    const play = () => {
      video.volume = volume / 100;
      video.muted = false;
      video.play().catch(() => {});
      setIsPlaying(true);
    };
    if (video.readyState >= 2) {
      play();
    } else {
      video.addEventListener('canplay', play, { once: true });
    }
  }, [isHovering, videoSrc, volume]);

  // Pause when mouse leaves
  useEffect(() => {
    if (!isHovering && isPlaying) {
      videoRef.current?.pause();
      setIsPlaying(false);
    }
  }, [isHovering, isPlaying]);

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

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !isMuted;
    setIsMuted(next);
    if (videoRef.current) videoRef.current.muted = next;
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    const vol = parseInt(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol / 100;
      const nowMuted = vol === 0;
      setIsMuted(nowMuted);
      videoRef.current.muted = nowMuted;
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
    if (video?.duration) {
      setProgress((video.currentTime / video.duration) * 100);
    }
  };

  return (
    <div
      className={`clip-preview${isDemoMode() ? ' demo-cover' : ''}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <div className="blur-bg-container">
        <img src={clip.thumbnail_url} alt="" draggable={false} />
      </div>
      <img
        src={clip.thumbnail_url}
        className="clip-thumbnail"
        alt={clip.title}
        draggable={false}
        style={{ opacity: isPlaying ? 0 : 1 }}
      />
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
      <div className={`video-loading ${isLoading ? 'active' : ''}`} />

      <button
        className="fullscreen-btn"
        onClick={(e) => {
          e.stopPropagation();
          onOpenTheater();
        }}
        title="Theater Mode"
      >
        ⛶
      </button>
      <button className="play-pause-btn" onClick={handlePlayPause} title="Play/Pause">
        {isPlaying ? '⏸' : '▶'}
      </button>

      <div className="volume-control">
        <button className="volume-btn" onClick={toggleMute}>
          <span>{volume === 0 ? '🔇' : '🔊'}</span>
        </button>
        <input
          type="range"
          className="volume-slider"
          min="0"
          max="100"
          value={volume}
          onChange={handleVolumeChange}
        />
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
          style={{
            background: `linear-gradient(to right, #ec4899 ${progress}%, rgba(255,255,255,0.2) ${progress}%)`,
          }}
        />
      </div>

      {children}
    </div>
  );
});
