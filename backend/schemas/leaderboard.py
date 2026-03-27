from typing import List
from pydantic import BaseModel, ConfigDict


class LeaderboardClip(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
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


LeaderboardResponse = List[LeaderboardClip]
