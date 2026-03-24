from typing import List
from pydantic import BaseModel


class LeaderboardClip(BaseModel):
    id: str
    title: str
    url: str
    thumbnail_url: str
    view_count: int
    creator_name: str
    duration: float
    created_at: str
    channel: str
    local_likes: int
    comment_count: int

    class Config:
        from_attributes = True


LeaderboardResponse = List[LeaderboardClip]
