from typing import List
from fastapi import APIRouter, Depends

from backend.core.state import AppState, get_state
from backend.schemas.leaderboard import LeaderboardClip

router = APIRouter(prefix="/api", tags=["leaderboard"])


@router.get("/leaderboard", response_model=List[LeaderboardClip])
async def get_leaderboard(
    state: AppState = Depends(get_state),
) -> List[LeaderboardClip]:
    clips = await state.get_leaderboard()
    return clips


@router.get("/leaderboard/fresh", response_model=List[LeaderboardClip])
async def get_leaderboard_fresh(
    state: AppState = Depends(get_state),
) -> List[LeaderboardClip]:
    """Get fresh leaderboard data immediately (for quick updates after votes)."""
    clips = await state.get_leaderboard()
    return clips
