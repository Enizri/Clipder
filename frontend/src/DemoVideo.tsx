import React, { useRef, useEffect } from 'react';

interface DemoVideoProps {
  isVisible?: boolean;
}

export const DemoVideo: React.FC<DemoVideoProps> = () => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.play();
    }
  }, []);

  return (
    <div
      style={{
        width: '100%',
        maxWidth: '900px',
        height: '500px',
        margin: '30px auto 40px',
        borderRadius: '20px',
        overflow: 'hidden',
        position: 'relative',
        background: '#000',
      }}
    >
      {/* Video Background */}
      <video
        ref={videoRef}
        src="/videos/aidemo.mp4"
        autoPlay
        loop
        muted
        playsInline
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: 'block',
        }}
      />

      {/* Enhanced Gradient Overlay for blending */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `
            linear-gradient(
              135deg,
              rgba(10, 14, 39, 0.1) 0%,
              rgba(30, 27, 75, 0.05) 50%,
              rgba(96, 165, 250, 0.08) 100%
            )
          `,
          pointerEvents: 'none',
          zIndex: 2,
        }}
      />

      {/* Glowing Border Effect */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          borderRadius: '20px',
          border: '2px solid rgba(96, 165, 250, 0.4)',
          pointerEvents: 'none',
          zIndex: 3,
          boxShadow: `
            inset 0 0 30px rgba(96, 165, 250, 0.2),
            0 0 40px rgba(96, 165, 250, 0.3),
            0 15px 40px rgba(0, 0, 0, 0.4)
          `,
        }}
      />

      {/* Animated Glow Effect */}
      <div
        style={{
          position: 'absolute',
          top: '-50%',
          left: '-50%',
          width: '200%',
          height: '200%',
          background: `
            radial-gradient(
              circle,
              rgba(168, 85, 247, 0.1) 0%,
              transparent 70%
            )
          `,
          animation: 'demoPulse 4s ease-in-out infinite',
          pointerEvents: 'none',
          zIndex: 1,
          borderRadius: '50%',
        }}
      />

      {/* Badge Label */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          color: '#ffffff',
          fontSize: '12px',
          fontWeight: '700',
          letterSpacing: '1.2px',
          zIndex: 10,
          textShadow: '0 2px 8px rgba(0, 0, 0, 0.6)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(0, 0, 0, 0.4)',
          padding: '8px 14px',
          borderRadius: '20px',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(96, 165, 250, 0.3)',
        }}
      >
        <span
          style={{
            width: '8px',
            height: '8px',
            background: '#60a5fa',
            borderRadius: '50%',
            animation: 'demoIndicatorPulse 1.5s ease-in-out infinite',
            boxShadow: '0 0 12px rgba(96, 165, 250, 1)',
          }}
        />
        AI EDITOR DEMO
      </div>

      {/* Bottom gradient accent */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: '100%',
          height: '60px',
          background: 'linear-gradient(to top, rgba(0, 0, 0, 0.3), transparent)',
          pointerEvents: 'none',
          zIndex: 2,
        }}
      />

      <style>{`
        @keyframes demoPulse {
          0%, 100% {
            transform: scale(1);
            opacity: 0.8;
          }
          50% {
            transform: scale(1.1);
            opacity: 0.4;
          }
        }

        @keyframes demoIndicatorPulse {
          0%, 100% {
            opacity: 1;
            box-shadow: 0 0 12px rgba(96, 165, 250, 1);
          }
          50% {
            opacity: 0.4;
            box-shadow: 0 0 6px rgba(96, 165, 250, 0.5);
          }
        }
      `}</style>
    </div>
  );
};
