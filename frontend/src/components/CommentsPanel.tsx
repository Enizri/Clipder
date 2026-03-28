import React, { useRef, useState } from 'react';
import { EmotePicker } from './EmotePicker';
import type { Comment } from '../types';

interface CommentsPanelProps {
  show: boolean;
  onClose: () => void;
  activeClip: { id: string; title: string } | null;
  comments: Comment[];
  onPostComment: (text: string) => void;
}

export const CommentsPanel: React.FC<CommentsPanelProps> = ({
  show,
  onClose,
  activeClip,
  comments,
  onPostComment,
}) => {
  const commentInputRef = useRef<HTMLDivElement>(null);
  const [showEmotePicker, setShowEmotePicker] = useState(false);

  const handlePost = () => {
    if (!commentInputRef.current) return;
    const text = commentInputRef.current.innerHTML.trim();
    if (!text || text === '<br>') return;
    commentInputRef.current.innerHTML = '';
    onPostComment(text);
  };

  const handleEmoteSelect = (url: string, code: string) => {
    if (!commentInputRef.current) return;
    const img = document.createElement('img');
    img.src = url;
    img.className = 'chat-emote';
    img.alt = code;
    commentInputRef.current.appendChild(img);
    // Non-breaking space keeps the cursor after the emote
    commentInputRef.current.appendChild(document.createTextNode('\u00A0'));
    commentInputRef.current.focus();
  };

  return (
    <div id="comments-sidebar" className={show ? 'show' : ''}>
      <div className="comments-header">
        <span>{activeClip?.title || 'Comments'}</span>
        <button className="close-comments" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="comments-list">
        {comments.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#666' }}>
            No comments yet. Be the first!
          </div>
        ) : (
          comments.map((c) => (
            <div key={c.timestamp} className="comment-item">
              <div className="comment-user">{c.user}</div>
              {/* User comments may contain emote img tags — render as HTML */}
              <div className="comment-text" dangerouslySetInnerHTML={{ __html: c.text }} />
            </div>
          ))
        )}
      </div>

      <div className="comments-input-wrapper">
        {showEmotePicker && (
          <EmotePicker
            onSelect={handleEmoteSelect}
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
              handlePost();
            }
          }}
        />
        <button
          className="emote-toggle-btn"
          onClick={() => setShowEmotePicker((s) => !s)}
        >
          ☺
        </button>
        <button className="send-btn" onClick={handlePost}>
          Send
        </button>
      </div>
    </div>
  );
};
