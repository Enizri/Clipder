import React, { useRef, useEffect } from 'react';

interface TheaterModeProps {
  src: string | null;
  loading: boolean;
  onClose: () => void;
}

export const TheaterMode: React.FC<TheaterModeProps> = ({ src, loading, onClose }) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (src && videoRef.current) {
      videoRef.current.volume = 0.05;
    }
  }, [src]);

  const visible = loading || src !== null;
  if (!visible) return null;

  return (
    <div id="theater-modal" className="show" style={{ display: 'flex' }}>
      <div className="theater-backdrop" onClick={onClose} />
      <button className="theater-close" onClick={onClose}>
        ✕
      </button>
      <div className="theater-content">
        <div className="theater-video-wrapper">
          {loading ? (
            <div
              style={{
                width: '100%',
                aspectRatio: '16/9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#000',
                borderRadius: '16px',
              }}
            >
              <div className="video-loading active" />
            </div>
          ) : (
            src && (
              <video
                id="theater-video"
                ref={videoRef}
                controls
                autoPlay
                src={src}
              />
            )
          )}
        </div>
      </div>
    </div>
  );
};
