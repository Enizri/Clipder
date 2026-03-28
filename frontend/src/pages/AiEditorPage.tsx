import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { DemoVideo } from '../DemoVideo';
import type { AdminClip, User } from '../types';

interface AiMessage {
  _id: number;
  role: 'user' | 'assistant';
  content: string;
  thumbnail_url?: string;
  video_url?: string;
  type?: string;
}

interface AiEditorPageProps {
  user: User | null;
}

// Gate: show pricing when no user OR user is plain USER role
const isProUser = (user: User | null) =>
  user?.role === 'PRO' || user?.role === 'ADMIN';

export const AiEditorPage: React.FC<AiEditorPageProps> = ({ user }) => {
  const [showPricing, setShowPricing] = useState(!isProUser(user));
  const [queue, setQueue] = useState<AdminClip[]>([]);
  const [chatMessages, setChatMessages] = useState<AiMessage[]>([]);
  const [input, setInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [selectedClip, setSelectedClip] = useState<AdminClip | null>(null);
  const [hoveredClipId, setHoveredClipId] = useState<string | null>(null);
  const [hoveredVideoUrl, setHoveredVideoUrl] = useState<string | null>(null);
  const hoverVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  // Re-evaluate pricing gate when user changes (e.g. login in another tab)
  useEffect(() => {
    setShowPricing(!isProUser(user));
  }, [user]);

  // Load saved clip history for the queue
  useEffect(() => {
    if (!isProUser(user)) return;
    api
      .getUserClipHistory()
      .then((response) => {
        const items = (response.history || []).map((item: any) => ({
          id: item.clip_id,
          title: item.clip_title,
          url: item.clip_url,
          channel: item.clip_channel,
          thumbnail_url: item.thumbnail_url,
          view_count: 0,
          creator_name: '',
          duration: 0,
          created_at: '',
        }));
        // Deduplicate by id
        const seen = new Set<string>();
        const unique = items.filter((c: AdminClip) => {
          if (seen.has(c.id)) return false;
          seen.add(c.id);
          return true;
        });
        setQueue(unique);
      })
      .catch(() => {
        // History load failed — show empty queue
      });
  }, [user]);

  const handleRemoveFromQueue = async (clipId: string) => {
    setQueue((prev) => prev.filter((c) => c.id !== clipId));
    try {
      await api.deleteClipFromHistory(clipId);
    } catch {
      // Removal from DB failed — UI already updated
    }
  };

  const handleDropClip = (clip: AdminClip) => {
    setSelectedClip(clip);
    setChatMessages((prev) => [
      ...prev,
      { _id: Date.now(), role: 'user', content: clip.title, thumbnail_url: clip.thumbnail_url, type: 'clip' },
    ]);
    setTimeout(() => {
      setChatMessages((prev) => [
        ...prev,
        { _id: Date.now() + 1, role: 'assistant', content: 'How can I make you money today? ;)' },
      ]);
    }, 800);
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedClip || aiLoading) return;

    const userMsg = input.trim();
    setInput('');
    setAiLoading(true);
    setChatMessages((prev) => [...prev, { _id: Date.now(), role: 'user', content: userMsg }]);

    try {
      const response = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clip_title: selectedClip.title,
          clip_channel: selectedClip.channel,
          user_message: userMsg,
          conversation_history: chatMessages,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setChatMessages((prev) => [
        ...prev,
        { _id: Date.now(), role: 'assistant', content: data.response },
      ]);
    } catch (err) {
      console.error('AI chat error:', err);
      setChatMessages((prev) => [
        ...prev,
        { _id: Date.now(), role: 'assistant', content: "Sorry, I couldn't process your request. Please try again." },
      ]);
    } finally {
      setAiLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // PRICING VIEW
  // ---------------------------------------------------------------------------

  if (showPricing) {
    return (
      <div
        id="ai-editor"
        className="view-section active"
        style={{ display: 'flex', flexDirection: 'column', padding: '20px', overflow: 'auto', alignItems: 'center' }}
      >
        <div style={{ width: '100%', maxWidth: '1400px' }}>
          <div className="pricing-hero">
            <h2>🚀 AI Editor Pro</h2>
            <p>Transform your clips with AI-powered editing suggestions. Get pro-level edits in seconds, not hours.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px', alignItems: 'start', marginBottom: '40px' }}>
            <div>
              <DemoVideo />
            </div>

            <div>
              <div className="pricing-cards">
                {/* Free Trial */}
                <div className="pricing-card">
                  <div className="card-header">
                    <div className="card-title">Free Trial</div>
                    <div className="card-price">Free</div>
                  </div>
                  <p className="card-description">Get started with limited AI editing credits</p>
                  <div className="card-benefits">
                    <div className="benefit-item"><span className="benefit-icon">⭐</span><span>3 AI edits per month</span></div>
                    <div className="benefit-item"><span className="benefit-icon">✨</span><span>Basic editing suggestions</span></div>
                    <div className="benefit-item"><span className="benefit-icon">🎬</span><span>720p preview quality</span></div>
                    <div className="benefit-item"><span className="benefit-icon">⏱</span><span>No expiration</span></div>
                  </div>
                  <button className="pricing-btn pricing-btn-secondary" onClick={() => setShowPricing(false)}>
                    Start Free Trial
                  </button>
                </div>

                {/* Pro Monthly */}
                <div className="pricing-card">
                  <div className="card-header">
                    <div className="card-title">Pro Monthly</div>
                    <div className="card-price">$9.99<span className="card-price-period">/mo</span></div>
                  </div>
                  <p className="card-description">Perfect for serious content creators</p>
                  <div className="card-benefits">
                    <div className="benefit-item"><span className="benefit-icon">⭐</span><span>Unlimited AI edits</span></div>
                    <div className="benefit-item"><span className="benefit-icon">✨</span><span>Advanced multi-prompt suggestions</span></div>
                    <div className="benefit-item"><span className="benefit-icon">🎬</span><span>1080p + HD exports</span></div>
                    <div className="benefit-item"><span className="benefit-icon">⚙️</span><span>Priority support</span></div>
                  </div>
                  <button className="pricing-btn pricing-btn-primary" onClick={() => setShowPricing(false)}>
                    Upgrade to Pro
                  </button>
                </div>

                {/* Pro Yearly */}
                <div className="pricing-card featured">
                  <div className="featured-badge">BEST VALUE 40% OFF</div>
                  <div className="card-header">
                    <div className="card-title">Pro Yearly</div>
                    <div className="card-price">$71.88<span className="card-price-period">/yr</span></div>
                  </div>
                  <p className="card-description">Save $47.88 vs monthly. Most popular choice.</p>
                  <div className="card-benefits">
                    <div className="benefit-item"><span className="benefit-icon">💎</span><span>All Pro features + unlimited everything</span></div>
                    <div className="benefit-item"><span className="benefit-icon">🎬</span><span>4K export capabilities</span></div>
                    <div className="benefit-item"><span className="benefit-icon">🤖</span><span>Early access to new AI features</span></div>
                    <div className="benefit-item"><span className="benefit-icon">🚀</span><span>VIP priority support (24/7)</span></div>
                  </div>
                  <button className="pricing-btn pricing-btn-primary" onClick={() => setShowPricing(false)}>
                    Get Yearly Deal
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="pricing-footer">
            <p>🎁 <span className="limited-offer">Limited time: First month 50% off any plan!</span></p>
            <p style={{ fontSize: '0.8em', color: '#666' }}>Cancel anytime. No hidden fees.</p>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // AI EDITOR VIEW (Pro / Trial)
  // ---------------------------------------------------------------------------

  return (
    <div
      id="ai-editor"
      className="view-section active"
      style={{ display: 'flex', flexDirection: 'column', padding: '20px', overflow: 'auto', alignItems: 'center' }}
    >
      <div style={{ width: '100%', height: '100%', display: 'flex', gap: '16px', position: 'relative', padding: '20px' }}>
        {/* CHAT SECTION */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <video
            src="/videos/maya.mp4"
            autoPlay
            loop
            muted
            playsInline
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover', opacity: 0.15, zIndex: 0, pointerEvents: 'none', borderRadius: '14px' }}
          />
          <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <h2 style={{ marginBottom: '20px', textAlign: 'center' }}>✨ AI Editor Playground</h2>

            <div
              className="ai-chat-panel"
              style={{ background: 'rgba(30,30,40,0.08)', borderRadius: '14px', border: '1px solid rgba(100,100,120,0.2)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', flex: 1, minHeight: 0, backdropFilter: 'blur(2px)' }}
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('drop-active'); }}
              onDragLeave={(e) => e.currentTarget.classList.remove('drop-active')}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('drop-active');
                const clipDataStr = e.dataTransfer?.getData('clipData');
                if (clipDataStr) {
                  try {
                    const clip = JSON.parse(clipDataStr);
                    handleDropClip(clip);
                  } catch {
                    // Malformed drag data — ignore
                  }
                }
              }}
            >
              <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {chatMessages.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.5)', margin: 'auto', fontSize: '0.95em' }}>
                    💡 Drag a clip from the right to start editing!
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div key={msg._id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                      {msg.type === 'clip' && msg.thumbnail_url ? (
                        <div style={{ maxWidth: '280px', overflow: 'hidden', borderRadius: '12px', border: '1px solid rgba(100,100,120,0.2)' }}>
                          <video poster={msg.thumbnail_url} style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '10px' }} />
                          <div style={{ background: 'rgba(30,30,40,0.5)', backdropFilter: 'blur(2px)', color: 'rgba(255,255,255,0.8)', padding: '8px 12px', fontSize: '0.85em', textAlign: 'center' }}>
                            {msg.content}
                          </div>
                        </div>
                      ) : (
                        <div style={{ background: 'rgba(59,130,246,0.08)', backdropFilter: 'blur(2px)', color: 'white', padding: '12px 14px', borderRadius: '12px', maxWidth: '75%', wordWrap: 'break-word' }}>
                          {msg.content}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={selectedClip ? 'Describe your editing vision...' : 'Drop a clip first to start chatting'}
                  disabled={!selectedClip}
                  style={{ flex: 1, padding: '10px 14px', background: 'rgba(30,41,59,0.6)', border: '1px solid rgba(147,51,234,0.2)', borderRadius: '8px', color: 'white' }}
                />
                <button
                  onClick={handleSend}
                  disabled={!selectedClip || aiLoading}
                  style={{ padding: '10px 16px', background: 'linear-gradient(135deg, #9333ea, #ec4899)', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer', opacity: !selectedClip || aiLoading ? 0.5 : 1 }}
                >
                  Send ✨
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* QUEUE SECTION */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: 'calc(100vh - 80px)', width: '320px', background: 'rgba(30,30,40,0.15)', borderRadius: '14px', border: '1px solid rgba(100,100,120,0.15)', padding: '16px', overflowY: 'auto', flexShrink: 0, position: 'relative', backdropFilter: 'blur(2px)' }}>
          <h3 style={{ color: '#f472b6', margin: 0, fontSize: '0.95em', position: 'sticky', top: 0, zIndex: 10 }}>📺 Queue</h3>

          {queue.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', padding: '40px 10px', fontSize: '0.85em' }}>
              <div style={{ fontSize: '2em', marginBottom: '8px' }}>📤</div>
              <div>Send clips from the swipe feed</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '60px' }}>
              {queue.map((clip) => (
                <div
                  key={clip.id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('clipData', JSON.stringify(clip));
                  }}
                  onMouseEnter={async (e) => {
                    (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)';
                    setHoveredClipId(clip.id);
                    if (!hoveredVideoUrl || hoveredClipId !== clip.id) {
                      try {
                        const data = await api.getVideoUrl(clip.id);
                        if (data.video_url) {
                          setHoveredVideoUrl(data.video_url);
                          setTimeout(() => hoverVideoRefs.current[clip.id]?.play().catch(() => {}), 50);
                        }
                      } catch {
                        // Video preview failed — thumbnail stays
                      }
                    }
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
                    setHoveredClipId(null);
                    hoverVideoRefs.current[clip.id]?.pause();
                  }}
                  style={{ position: 'relative', borderRadius: '10px', overflow: 'hidden', border: '2px solid rgba(236,72,153,0.4)', cursor: 'grab', transition: 'transform 0.2s, opacity 0.2s', background: 'rgba(0,0,0,0.5)', height: '85px', backgroundImage: `url(${clip.thumbnail_url})`, backgroundSize: 'cover', backgroundPosition: 'center', flexShrink: 0 }}
                  onClick={() => handleDropClip(clip)}
                >
                  <div style={{ width: '100%', height: '100%', background: 'linear-gradient(to bottom, transparent, rgba(0,0,0,0.8))', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', padding: '6px' }}>
                    <div style={{ textAlign: 'center', fontSize: '0.65em', color: 'rgba(255,255,255,0.9)', lineHeight: '1.1', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', fontWeight: 500 }}>
                      {clip.title}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRemoveFromQueue(clip.id); }}
                    style={{ position: 'absolute', top: '4px', right: '4px', width: '22px', height: '22px', background: 'rgba(239,68,68,0.9)', border: 'none', borderRadius: '50%', color: 'white', cursor: 'pointer', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0, zIndex: 100 }}
                    title="Remove from queue"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
