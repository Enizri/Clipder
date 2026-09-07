from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Literal, Optional


class ChatMessage(BaseModel):
    """Single message in chat conversation."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class EditAction(BaseModel):
    """Single edit action in timeline."""

    action: str  # 'title_edit', 'description_edit', 'tag_added', etc.
    timestamp: str
    before: Optional[str] = None
    after: Optional[str] = None


class ClipHistoryCreate(BaseModel):
    """Request to save a clip to user history."""

    clip_id: str
    clip_title: str
    clip_url: str
    clip_channel: str
    thumbnail_url: Optional[str] = None
    clip_description: Optional[str] = None
    clip_tags: Optional[List[str]] = None
    edited_title: Optional[str] = None
    chat_messages: Optional[List[ChatMessage]] = None
    edit_history: Optional[List[EditAction]] = None


class ClipHistoryResponse(BaseModel):
    """Response for a single clip in user history."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    clip_id: str
    clip_title: str
    clip_url: str
    clip_channel: str
    thumbnail_url: Optional[str] = None
    clip_description: Optional[str] = None
    clip_tags: Optional[str] = None  # Stored as JSON string
    edited_title: Optional[str] = None
    chat_messages: Optional[str] = None  # Stored as JSON string
    edit_history: Optional[str] = None  # Stored as JSON string
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_edited_at: Optional[datetime] = None


class UserClipHistoryResponse(BaseModel):
    """Response with list of user's clip history."""

    history: List[ClipHistoryResponse] = Field(default_factory=list)
    total: int


class DeleteHistoryResponse(BaseModel):
    """Response after deleting a history item."""

    status: str
    message: str


class AnalyzeClipResponse(BaseModel):
    """Groq (or demo) analysis of a queued playground clip."""

    transcript: str
    score: float = Field(..., ge=0.0, le=1.0)
    title: str
    description: str


class UploadClipRequest(BaseModel):
    """Requested social destinations for a queued clip."""

    platforms: List[Literal["youtube_shorts", "tiktok"]] = Field(
        ..., min_length=1
    )


class UploadClipResponse(BaseModel):
    """Queued multi-platform export. Live adapters in engine.py are stubs."""

    status: str
    youtube: Optional[str] = None
    tiktok: bool = False
    message: str
