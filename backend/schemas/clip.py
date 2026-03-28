from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ClipBase(BaseModel):
    id: str
    title: str
    url: str
    thumbnail_url: str
    view_count: int
    creator_name: str
    duration: float
    created_at: str
    channel: str


class ClipResponse(ClipBase):
    model_config = ConfigDict(from_attributes=True)

    local_likes: int = 0
    comment_count: int = 0


class ClipsResponse(BaseModel):
    clips: List[ClipResponse]
    total: int


class VideoUrlResponse(BaseModel):
    video_url: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None


class ClipActionRequest(BaseModel):
    action: str = Field(..., pattern="^(like|dislike)$")


class ClipActionResponse(BaseModel):
    status: str
    current_score: int


class Comment(BaseModel):
    user: str
    text: str
    timestamp: str


class CommentResponse(BaseModel):
    status: str = "success"
    comment: Optional[Comment] = None


class CategoryResponse(BaseModel):
    categories: List[str]


class EmoteItem(BaseModel):
    code: str
    id: str
    url: str


class EmoteResponse(BaseModel):
    twitch: List[Dict[str, str]]
    bttv: List[Dict[str, str]]
    seventv: List[Dict[str, str]]
    channel: List[Dict[str, str]] = []


