"""Pydantic schemas for leaderboard snapshots."""

from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class LeaderboardSnapshotResponse(BaseModel):
    """Response schema for a single leaderboard snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_month: str = Field(..., description="Month in YYYY-MM format")
    snapshot_timestamp: datetime
    ranking: List[Dict[str, Any]] = Field(..., description="Array of ranked clips")
    created_at: datetime


class LeaderboardSnapshotCreate(BaseModel):
    """Schema for creating a new snapshot."""

    snapshot_month: str
    snapshot_timestamp: datetime
    ranking: List[Dict[str, Any]]


class LeaderboardHistoryResponse(BaseModel):
    """Response for leaderboard history query."""

    month: str
    snapshots_count: int
    first_snapshot: datetime
    last_snapshot: datetime
    latest_ranking: List[Dict[str, Any]]
