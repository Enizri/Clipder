import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { isDemoMode, readDemoQueue, removeDemoQueue } from '../demo/demoClips';
import type { AdminClip, User } from '../types';

interface AiMessage {
  _id: number;
  role: 'user' | 'assistant';
  content: string;
  thumbnail_url?: string;
  video_url?: string;
  type?: string;
}

interface QueueClip extends AdminClip {
  marked_for_export: boolean;
  transcript?: string;
  analysisTitle?: string;
  analysisScore?: number;
  analysisDescription?: string;
  analyzing?: boolean;
  uploading?: boolean;
}

interface AiEditorPageProps {
  user: User | null;
  onShowAuth: () => void;
}

function isMarkedForExport(editHistory: unknown): boolean {
  if (!editHistory) return false;
  let actions: unknown = editHistory;
  if (typeof editHistory === 'string') {
    try {
      actions = JSON.parse(editHistory);
    } catch {
      return false;
    }
  }
  if (!Array.isArray(actions)) return false;
  return actions.some(
    (item) =>
      item &&
      typeof item === 'object' &&
      (item as { action?: string }).action === 'marked_for_export',
  );
}

export const AiEditorPage: React.FC<AiEditorPageProps> = ({ user, onShowAuth }) => {
  const [queue, setQueue] = useState<QueueClip[]>([]);
  const [chatMessages, setChatMessages] = useState<AiMessage[]>([]);
  const [input, setInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [selectedClip, setSelectedClip] = useState<QueueClip | null>(null);
  const [hoveredClipId, setHoveredClipId] = useState<string | null>(null);
  const [hoveredVideoUrl, setHoveredVideoUrl] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const hoverVideoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  useEffect(() => {
    if (!user) {
      setQueue([]);
      return;
    }
    if (isDemoMode()) {
      setQueue(
        readDemoQueue().map((item) => ({
          id: item.id,
          title: item.title,
          url: item.url,
          channel: item.channel,
          thumbnail_url: item.thumbnail_url,
          view_count: item.view_count,
          creator_name: item.creator_name,
          duration: item.duration,
          created_at: item.created_at,
          marked_for_export: false,
        })),
      );
      return;
    }
    api
      .getUserClipHistory()
      .then((response) => {
        const items = (response.history || []).map((item) => ({
          id: item.clip_id,
          title: item.clip_title,
          url: item.clip_url,
          channel: item.clip_channel,
          thumbnail_url: item.thumbnail_url || '',
          view_count: 0,
          creator_name: item.clip_channel,
          duration: 0,
          created_at: '',
          marked_for_export: isMarkedForExport(item.edit_history),
        }));
        const seen = new Set<string>();
        const unique = items.filter((c: QueueClip) => {
          if (seen.has(c.id)) return false;
          seen.add(c.id);
          return true;
        });
        setQueue(unique);
      })
      .catch(() => {
        setQueue([]);
      });
  }, [user]);

  const handleRemoveFromQueue = async (clipId: string) => {
    setQueue((prev) => prev.filter((c) => c.id !== clipId));
    if (selectedClip?.id === clipId) {
      setSelectedClip(null);
      setChatMessages([]);
    }
    if (isDemoMode()) {
      removeDemoQueue(clipId);
      return;
    }
    try {
      await api.deleteClipFromHistory(clipId);
    } catch {
      // UI already updated
    }
  };

  const handleAnalyze = async (clip: QueueClip) => {
    setSelectedClip(clip);
    setQueue((prev) => prev.map((c) => (c.id === clip.id ? { ...c, analyzing: true } : c)));
    setStatusMessage('Groq is transcribing and scoring this clip…');
    try {
      let transcript: string;
      let score: number;
      let title: string;
      let description: string;
      if (isDemoMode()) {
        await new Promise((r) => setTimeout(r, 700));
        transcript = `[00:02] wait wait wait — ${clip.title.toLowerCase()}
[00:08] chat is going crazy
[00:14] that's the clip. that's the one.`;
        score = 0.86;
        title = `${clip.title} 🔥`;
        description = `${clip.title} — cut for YouTube Shorts & TikTok. #twitch #gaming`;
      } else {
        const data = await api.analyzeClip(clip.id);
        transcript = data.transcript;
        score = data.score;
        title = data.title;
        description = data.description;
      }
      setQueue((prev) =>
        prev.map((c) =>
          c.id === clip.id
            ? {
                ...c,
                analyzing: false,
                transcript,
                analysisScore: score,
                analysisTitle: title,
                analysisDescription: description,
              }
            : c,
        ),
      );
      setSelectedClip((prev) =>
        prev && prev.id === clip.id
          ? { ...prev, transcript, analysisScore: score, analysisTitle: title, analysisDescription: description }
          : prev,
      );
      setChatMessages((prev) => [
        ...prev,
        {
          _id: Date.now(),
          role: 'assistant',
          content: `Transcript ready (score ${Math.round(score * 100)}%).\n\n${transcript}\n\nSuggested title: ${title}`,
        },
      ]);
      setStatusMessage('Analysis done. Upload to YouTube Shorts and TikTok when you want.');
    } catch {
      setQueue((prev) => prev.map((c) => (c.id === clip.id ? { ...c, analyzing: false } : c)));
      setStatusMessage('Analysis failed. Try again.');
    }
  };

  const handleUpload = async (clip: QueueClip) => {
    if (!clip.transcript) {
      await handleAnalyze(clip);
    }
    setQueue((prev) => prev.map((c) => (c.id === clip.id ? { ...c, uploading: true } : c)));
    setStatusMessage('Queuing YouTube Shorts and TikTok…');
    try {
      if (isDemoMode()) {
        await new Promise((r) => setTimeout(r, 600));
      } else {
        await api.uploadClip(clip.id, ['youtube_shorts', 'tiktok']);
      }
      setQueue((prev) =>
        prev.map((c) =>
          c.id === clip.id ? { ...c, uploading: false, marked_for_export: true } : c,
        ),
      );
      setChatMessages((prev) => [
        ...prev,
        {
          _id: Date.now(),
          role: 'assistant',
          content:
            'Queued for YouTube Shorts and TikTok. Live publish still needs platform credentials — this records the export decision.',
        },
      ]);
      setStatusMessage('Queued for YouTube Shorts + TikTok.');
    } catch {
      setQueue((prev) => prev.map((c) => (c.id === clip.id ? { ...c, uploading: false } : c)));
      setStatusMessage('Upload queue failed.');
    }
  };

  const handleDropClip = (clip: QueueClip) => {
    setSelectedClip(clip);
    setChatMessages((prev) => [
      ...prev,
      {
        _id: Date.now(),
        role: 'user',
        content: clip.title,
        thumbnail_url: clip.thumbnail_url,
        type: 'clip',
      },
    ]);
    setTimeout(() => {
      setChatMessages((prev) => [
        ...prev,
        {
          _id: Date.now() + 1,
          role: 'assistant',
          content:
            'Ask for titles, hooks, or Shorts/TikTok cuts. This uses Groq in the cloud — nothing runs on your laptop.',
        },
      ]);
    }, 400);
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedClip || aiLoading) return;

    const userMsg = input.trim();
    setInput('');
    setAiLoading(true);
    setChatMessages((prev) => [...prev, { _id: Date.now(), role: 'user', content: userMsg }]);

    try {
      const history = chatMessages
        .filter((m) => m.type !== 'clip')
        .map((m) => ({ role: m.role, content: m.content }));
      const data = await api.chatForClip({
        clip_title: selectedClip.title,
        clip_channel: selectedClip.channel,
        user_message: userMsg,
        conversation_history: history,
      });
      setChatMessages((prev) => [
        ...prev,
        { _id: Date.now(), role: 'assistant', content: data.response },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          _id: Date.now(),
          role: 'assistant',
          content: "Sorry, I couldn't process your request. Please try again.",
        },
      ]);
    } finally {
      setAiLoading(false);
    }
  };

  if (!user) {
    return (
      <div
        id="ai-editor"
        className="view-section active"
        style={{ display: 'flex', flexDirection: 'column', padding: '40px', alignItems: 'center' }}
      >
        <h2>Playground</h2>
        <p style={{ color: 'rgba(255,255,255,0.7)', maxWidth: '420px', textAlign: 'center' }}>
          Log in to send liked clips here. Swipe right on the feed to add a clip, then skip it or
          mark it for export.
        </p>
        <button className="auth-btn" type="button" onClick={onShowAuth} style={{ marginTop: '16px' }}>
          Log in
        </button>
      </div>
    );
  }

  return (
    <div
      id="ai-editor"
      className="view-section active"
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        overflow: 'auto',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          gap: '16px',
          position: 'relative',
          padding: '20px',
        }}
      >
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <h2 style={{ marginBottom: '8px', textAlign: 'center' }}>Playground</h2>
            <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.55)', fontSize: '0.85em', marginBottom: '16px' }}>
              Liked clips land here. Skip to drop them, or mark for export. AI chat uses Groq.
            </p>
            {statusMessage && (
              <p style={{ textAlign: 'center', color: 'rgba(244,114,182,0.9)', fontSize: '0.8em' }}>
                {statusMessage}
              </p>
            )}

            <div
              className="ai-chat-panel"
              style={{
                background: 'rgba(30,30,40,0.08)',
                borderRadius: '14px',
                border: '1px solid rgba(100,100,120,0.2)',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                flex: 1,
                minHeight: 0,
                backdropFilter: 'blur(2px)',
              }}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add('drop-active');
              }}
              onDragLeave={(e) => e.currentTarget.classList.remove('drop-active')}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('drop-active');
                const clipDataStr = e.dataTransfer?.getData('clipData');
                if (clipDataStr) {
                  try {
                    handleDropClip(JSON.parse(clipDataStr) as QueueClip);
                  } catch {
                    // ignore
                  }
                }
              }}
            >
              <div
                style={{
                  flex: 1,
                  background: 'rgba(0,0,0,0.2)',
                  borderRadius: '8px',
                  padding: '16px',
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                {chatMessages.length === 0 ? (
                  <div
                    style={{
                      textAlign: 'center',
                      color: 'rgba(255,255,255,0.5)',
                      margin: 'auto',
                      fontSize: '0.95em',
                    }}
                  >
                    Drag a clip from your queue, or click it, to start.
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg._id}
                      style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
                    >
                      {msg.type === 'clip' && msg.thumbnail_url ? (
                        <div
                          style={{
                            maxWidth: '280px',
                            overflow: 'hidden',
                            borderRadius: '12px',
                            border: '1px solid rgba(100,100,120,0.2)',
                          }}
                        >
                          <video
                            poster={msg.thumbnail_url}
                            style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '10px' }}
                          />
                          <div
                            style={{
                              background: 'rgba(30,30,40,0.5)',
                              color: 'rgba(255,255,255,0.8)',
                              padding: '8px 12px',
                              fontSize: '0.85em',
                              textAlign: 'center',
                            }}
                          >
                            {msg.content}
                          </div>
                        </div>
                      ) : (
                        <div
                          style={{
                            background: 'rgba(59,130,246,0.08)',
                            color: 'white',
                            padding: '12px 14px',
                            borderRadius: '12px',
                            maxWidth: '75%',
                            wordWrap: 'break-word',
                          }}
                        >
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
                  placeholder={
                    selectedClip ? 'Ask Groq for titles, hooks, or cuts…' : 'Select a clip first'
                  }
                  disabled={!selectedClip}
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    background: 'rgba(30,41,59,0.6)',
                    border: '1px solid rgba(147,51,234,0.2)',
                    borderRadius: '8px',
                    color: 'white',
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={!selectedClip || aiLoading}
                  style={{
                    padding: '10px 16px',
                    background: 'linear-gradient(135deg, #9333ea, #ec4899)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'white',
                    cursor: 'pointer',
                    opacity: !selectedClip || aiLoading ? 0.5 : 1,
                  }}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            height: 'calc(100vh - 80px)',
            width: '320px',
            background: 'rgba(30,30,40,0.15)',
            borderRadius: '14px',
            border: '1px solid rgba(100,100,120,0.15)',
            padding: '16px',
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <h3 style={{ color: '#f472b6', margin: 0, fontSize: '0.95em' }}>Your queue</h3>

          {queue.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                color: 'rgba(255,255,255,0.4)',
                padding: '40px 10px',
                fontSize: '0.85em',
              }}
            >
              <div style={{ fontSize: '2em', marginBottom: '8px' }}>📤</div>
              <div>Swipe right on a clip to add it here</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {queue.map((clip) => (
                <div
                  key={clip.id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('clipData', JSON.stringify(clip));
                  }}
                    onMouseEnter={async (e) => {
                    (e.currentTarget as HTMLElement).style.transform = 'scale(1.03)';
                    setHoveredClipId(clip.id);
                    if (isDemoMode()) return;
                    if (!hoveredVideoUrl || hoveredClipId !== clip.id) {
                      try {
                        const data = await api.getVideoUrl(clip.id);
                        if (data.video_url) {
                          setHoveredVideoUrl(data.video_url);
                          setTimeout(() => hoverVideoRefs.current[clip.id]?.play().catch(() => {}), 50);
                        }
                      } catch {
                        // thumbnail stays
                      }
                    }
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
                    setHoveredClipId(null);
                    hoverVideoRefs.current[clip.id]?.pause();
                  }}
                  style={{
                    position: 'relative',
                    borderRadius: '10px',
                    overflow: 'hidden',
                    border: clip.marked_for_export
                      ? '2px solid rgba(52,211,153,0.7)'
                      : '2px solid rgba(236,72,153,0.4)',
                    cursor: 'grab',
                    backgroundImage: `url(${clip.thumbnail_url})`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    minHeight: '110px',
                    flexShrink: 0,
                  }}
                  onClick={() => handleDropClip(clip)}
                >
                  <div
                    style={{
                      width: '100%',
                      minHeight: '110px',
                      background: 'linear-gradient(to bottom, transparent, rgba(0,0,0,0.85))',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'flex-end',
                      padding: '8px',
                      gap: '6px',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '0.7em',
                        color: 'rgba(255,255,255,0.95)',
                        fontWeight: 500,
                        lineHeight: 1.2,
                      }}
                    >
                      {clip.title}
                    </div>
                    {clip.transcript && (
                      <div
                        style={{
                          fontSize: '0.62em',
                          color: 'rgba(196,181,253,0.95)',
                          lineHeight: 1.35,
                          maxHeight: '3.2em',
                          overflow: 'hidden',
                        }}
                      >
                        {clip.analysisScore != null
                          ? `Score ${Math.round(clip.analysisScore * 100)}% · `
                          : ''}
                        {clip.transcript}
                      </div>
                    )}
                    {clip.marked_for_export && (
                      <span style={{ fontSize: '0.65em', color: '#6ee7b7' }}>
                        Queued · YouTube Shorts + TikTok
                      </span>
                    )}
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleRemoveFromQueue(clip.id);
                        }}
                        style={{
                          flex: 1,
                          padding: '4px 6px',
                          fontSize: '0.7em',
                          border: 'none',
                          borderRadius: '6px',
                          background: 'rgba(239,68,68,0.85)',
                          color: 'white',
                          cursor: 'pointer',
                        }}
                      >
                        Skip
                      </button>
                      <button
                        type="button"
                        data-testid={`btn-analyze-${clip.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDropClip(clip);
                          void handleAnalyze(clip);
                        }}
                        disabled={Boolean(clip.analyzing) || Boolean(clip.transcript)}
                        style={{
                          flex: 1,
                          padding: '4px 6px',
                          fontSize: '0.7em',
                          border: 'none',
                          borderRadius: '6px',
                          background: clip.transcript
                            ? 'rgba(139,92,246,0.45)'
                            : 'rgba(139,92,246,0.95)',
                          color: 'white',
                          cursor: clip.transcript || clip.analyzing ? 'default' : 'pointer',
                        }}
                      >
                        {clip.analyzing ? 'Analyzing…' : clip.transcript ? 'Analyzed' : 'Analyze'}
                      </button>
                    </div>
                    <button
                      type="button"
                      data-testid={`btn-upload-${clip.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDropClip(clip);
                        void handleUpload(clip);
                      }}
                      disabled={clip.marked_for_export || Boolean(clip.uploading)}
                      style={{
                        width: '100%',
                        padding: '6px 6px',
                        fontSize: '0.68em',
                        fontWeight: 700,
                        border: 'none',
                        borderRadius: '6px',
                        background: clip.marked_for_export
                          ? 'rgba(52,211,153,0.4)'
                          : 'rgba(16,185,129,0.95)',
                        color: 'white',
                        cursor: clip.marked_for_export || clip.uploading ? 'default' : 'pointer',
                      }}
                    >
                      {clip.uploading
                        ? 'Uploading…'
                        : clip.marked_for_export
                          ? 'Uploaded'
                          : 'Upload YouTube Shorts + TikTok'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
