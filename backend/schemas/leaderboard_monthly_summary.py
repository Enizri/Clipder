"""Pydantic schemas for leaderboard monthly summary."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class LeaderboardMonthlySummaryResponse(BaseModel):
    """Response schema for monthly summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_month: str = Field(..., description="Month in YYYY-MM format")
    final_ranking: List[Dict[str, Any]] = Field(..., description="Top 10 final ranking")
    total_votes: int
    total_unique_voters: int
    top_clip_id: Optional[int] = None
    top_clip_score: Optional[float] = None
    month_end_date: datetime
    created_at: datetime


class LeaderboardMonthlySummaryCreate(BaseModel):
    """Schema for creating monthly summary."""

    snapshot_month: str
    final_ranking: List[Dict[str, Any]]
    total_votes: int
    total_unique_voters: int
    top_clip_id: Optional[int] = None
    top_clip_score: Optional[float] = None
    month_end_date: datetime


class HistoricalLeaderboardResponse(BaseModel):
    """Response for historical leaderboard data (past months)."""

    months_available: List[str] = Field(
        ..., description="List of available months in YYYY-MM format"
    )
    leaderboards: List[LeaderboardMonthlySummaryResponse]


class LeaderboardStatsResponse(BaseModel):
    """Aggregated leaderboard statistics."""

    current_month: str
    total_clips_current_month: int
    total_votes_current_month: int
    avg_votes_per_clip: float
    top_clip_this_month: Optional[Dict[str, Any]] = None
    historical_months: int = Field(..., description="Number of archived months")
