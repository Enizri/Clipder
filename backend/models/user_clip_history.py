import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from backend.core.database import Base


class UserClipHistory(Base):
    """Stores clip history for PRO users in AI Editor with edits and chat."""

    __tablename__ = "user_clip_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    clip_id = Column(String, nullable=False, index=True)
    clip_title = Column(String, nullable=False)
    clip_url = Column(String, nullable=False)
    clip_channel = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)

    # Edits tracking (stored as JSON)
    clip_description = Column(String, nullable=True)  # User's custom description
    clip_tags = Column(Text, nullable=True)  # JSON array of tags
    edited_title = Column(String, nullable=True)  # Original vs edited title

    # Chat history (stored as JSON array)
    chat_messages = Column(
        Text, nullable=True
    )  # JSON array of {role, content, timestamp}

    # Timeline of all edits (stored as JSON array)
    edit_history = Column(
        Text, nullable=True
    )  # JSON array of {action, timestamp, before, after}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_edited_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("User", backref="clip_history")
