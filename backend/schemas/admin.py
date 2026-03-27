from typing import List
from pydantic import BaseModel, ConfigDict


class AdminClip(BaseModel):
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


class AddToQueueRequest(BaseModel):
    clip_id: str


class RemoveFromQueueRequest(BaseModel):
    clip_id: str


class QueueStatusResponse(BaseModel):
    status: str


class ProcessRequest(BaseModel):
    clip_ids: List[str]


class ProcessStatusResponse(BaseModel):
    status: str


AcceptedResponse = List[AdminClip]
