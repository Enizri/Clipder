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

let messageIdSeq = 0;

/** Monotonic keys — `Date.now()` collides when two messages are pushed in the same tick. */
function nextMessageId(): number {
  messageIdSeq += 1;
  return messageIdSeq;
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
  const chatLogRef = useRef<HTMLDivElement>(null);

  /** Keep the newest message in view so long transcripts do not push it out of frame. */
  useEffect(() => {
    const log = chatLogRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [chatMessages]);

  const handleCardHover = async (clip: QueueClip) => {
    setHoveredClipId(clip.id);
    if (isDemoMode() || hoveredClipId === clip.id) return;
    try {
      const data = await api.getVideoUrl(clip.id);
      if (!data.video_url) return;
      setHoveredVideoUrl(data.video_url);
      setTimeout(() => hoverVideoRefs.current[clip.id]?.play().catch(() => {}), 50);
    } catch {
      // thumbnail stays
    }
  };

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
    if (selectedClip?.id !== clip.id) {
      setChatMessages([]);
    }
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
          _id: nextMessageId(),
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
          _id: nextMessageId(),
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

  /** Opens a clip's thread. Re-selecting the open clip is a no-op so Analyze/Upload
   *  do not append a duplicate clip card and intro line. */
  const handleDropClip = (clip: QueueClip) => {
    if (selectedClip?.id === clip.id) return;
    setSelectedClip(clip);
    setChatMessages([
      {
        _id: nextMessageId(),
        role: 'user',
        content: clip.title,
        thumbnail_url: clip.thumbnail_url,
        type: 'clip',
      },
      {
        _id: nextMessageId(),
        role: 'assistant',
        content:
          'Ask for titles, hooks, or Shorts/TikTok cuts. This uses Groq in the cloud — nothing runs on your laptop.',
      },
    ]);
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedClip || aiLoading) return;

    const userMsg = input.trim();
    setInput('');
    setAiLoading(true);
    setChatMessages((prev) => [...prev, { _id: nextMessageId(), role: 'user', content: userMsg }]);

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
        { _id: nextMessageId(), role: 'assistant', content: data.response },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          _id: nextMessageId(),
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
    <div id="ai-editor" className="view-section active">
      <div className="playground-layout">
        <div className="playground-main">
          <h2 className="playground-heading">Playground</h2>
          <p className="playground-subtitle">
            Liked clips land here. Skip to drop them, or mark for export. AI chat uses Groq.
          </p>
          <p className="playground-status">{statusMessage}</p>

          <div
            className="ai-chat-panel playground-chat"
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
            <div className="playground-chat-log" ref={chatLogRef}>
              {selectedClip && (
                <div className="playground-active-clip">
                  <img src={selectedClip.thumbnail_url} alt="" draggable={false} />
                  <div className="playground-active-clip-copy">
                    <div className="playground-active-clip-title">{selectedClip.title}</div>
                    <div className="playground-active-clip-meta">
                      {selectedClip.creator_name || selectedClip.channel}
                    </div>
                  </div>
                </div>
              )}
              {chatMessages.filter((msg) => msg.type !== 'clip').length === 0 && !selectedClip ? (
                <div className="playground-chat-empty">
                  Drag a clip from your queue, or click it, to start.
                </div>
              ) : (
                chatMessages
                  .filter((msg) => msg.type !== 'clip')
                  .map((msg) => (
                    <div
                      key={msg._id}
                      className={`playground-msg ${msg.role === 'user' ? 'is-user' : 'is-assistant'}`}
                    >
                      <div className="playground-msg-bubble">{msg.content}</div>
                    </div>
                  ))
              )}
            </div>

            <div className="playground-chat-input-row">
              <input
                type="text"
                className="ai-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={
                  selectedClip ? 'Ask Groq for titles, hooks, or cuts…' : 'Select a clip first'
                }
                disabled={!selectedClip}
              />
              <button
                type="button"
                className="queue-btn queue-btn-analyze"
                style={{ flex: '0 0 auto', padding: '0 20px', fontSize: '0.85em' }}
                onClick={handleSend}
                disabled={!selectedClip || aiLoading}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        <aside className="queue-panel">
          <div className="queue-panel-header">
            <h3>Your queue</h3>
            {queue.length > 0 && (
              <span className="queue-panel-count">
                {queue.length} clip{queue.length === 1 ? '' : 's'}
              </span>
            )}
          </div>

          {queue.length === 0 ? (
            <div className="queue-empty">
              <div className="queue-empty-icon">📤</div>
              <div>Swipe right on a clip to add it here</div>
            </div>
          ) : (
            <div className="queue-list">
              {queue.map((clip) => (
                <article
                  key={clip.id}
                  className={`queue-card${clip.marked_for_export ? ' is-exported' : ''}`}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('clipData', JSON.stringify(clip));
                  }}
                  onMouseEnter={() => void handleCardHover(clip)}
                  onMouseLeave={() => {
                    setHoveredClipId(null);
                    hoverVideoRefs.current[clip.id]?.pause();
                  }}
                  onClick={() => handleDropClip(clip)}
                >
                  <div className="queue-card-media">
                    <img src={clip.thumbnail_url} alt="" draggable={false} loading="lazy" />
                    {hoveredClipId === clip.id && hoveredVideoUrl && (
                      <video
                        ref={(el) => {
                          hoverVideoRefs.current[clip.id] = el;
                        }}
                        className="is-playing"
                        src={hoveredVideoUrl}
                        muted
                        loop
                        playsInline
                      />
                    )}
                    {clip.marked_for_export && (
                      <span className="queue-card-badge">QUEUED</span>
                    )}
                    <button
                      type="button"
                      className="queue-card-remove"
                      title="Remove from queue"
                      aria-label={`Remove ${clip.title} from queue`}
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleRemoveFromQueue(clip.id);
                      }}
                    >
                      ✕
                    </button>
                  </div>

                  <div className="queue-card-body">
                    <div className="queue-card-title">{clip.title}</div>
                    <div className="queue-card-meta">
                      {clip.creator_name || clip.channel}
                      {clip.analysisScore != null
                        ? ` · Score ${Math.round(clip.analysisScore * 100)}%`
                        : ''}
                      {clip.marked_for_export ? ' · YouTube Shorts + TikTok' : ''}
                    </div>

                    <div className="queue-card-actions">
                      <button
                        type="button"
                        className="queue-btn queue-btn-analyze"
                        data-testid={`btn-analyze-${clip.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleAnalyze(clip);
                        }}
                        disabled={Boolean(clip.analyzing) || Boolean(clip.transcript)}
                      >
                        {clip.analyzing ? 'Analyzing…' : clip.transcript ? 'Analyzed' : 'Analyze'}
                      </button>
                      <button
                        type="button"
                        className="queue-btn queue-btn-upload"
                        data-testid={`btn-upload-${clip.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleUpload(clip);
                        }}
                        disabled={clip.marked_for_export || Boolean(clip.uploading)}
                      >
                        {clip.uploading
                          ? 'Uploading…'
                          : clip.marked_for_export
                            ? 'Uploaded'
                            : 'Upload Shorts + TikTok'}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};
