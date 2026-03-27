"""Pydantic schemas for leaderboard clip performance."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LeaderboardClipPerformanceResponse(BaseModel):
    """Response schema for clip performance data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    clip_id: int
    snapshot_month: str = Field(..., description="Month in YYYY-MM format")
    entered_top_10_at: Optional[datetime] = None
    exited_top_10_at: Optional[datetime] = None
    peak_rank: Optional[int] = None
    peak_score: Optional[float] = None
    total_time_in_top_10: Optional[int] = Field(None, description="Time in seconds")
    created_at: datetime
    updated_at: datetime


class LeaderboardClipPerformanceCreate(BaseModel):
    """Schema for creating clip performance record."""

    clip_id: int
    snapshot_month: str
    entered_top_10_at: Optional[datetime] = None
    exited_top_10_at: Optional[datetime] = None
    peak_rank: Optional[int] = None
    peak_score: Optional[float] = None


class ClipTrendResponse(BaseModel):
    """Response for clip trend over 24 hours."""

    clip_id: int
    title: str
    creator_name: str
    peak_rank: int
    current_rank: int
    score_trend: list = Field(..., description="Score values over time")
    rank_changes: int = Field(..., description="Number of rank changes")
