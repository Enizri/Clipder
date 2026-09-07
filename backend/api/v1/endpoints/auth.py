import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.v1.deps import get_current_user
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.security import create_access_token
from backend.core.twitch_oauth import TwitchOAuth
from backend.models import User, UserRole
from backend.api.v1.endpoints.following import sync_twitch_follows_for_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)

twitch_oauth = TwitchOAuth()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_pro: bool
    twitch_id: str | None = None
    twitch_username: str | None = None


class TwitchLoginResponse(BaseModel):
    authorization_url: str


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user from the JWT."""
    return UserResponse.model_validate(current_user)


@router.get("/twitch/login", response_model=TwitchLoginResponse)
async def twitch_login() -> TwitchLoginResponse:
    """Return the Twitch OAuth authorization URL — no auth required."""
    auth_url = twitch_oauth.get_authorization_url(state="")
    return TwitchLoginResponse(authorization_url=auth_url)


@router.get("/twitch/callback")
async def twitch_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Twitch OAuth callback — create-or-return flow.

    1. Exchange code for Twitch token
    2. Fetch Twitch user info (id, display_name)
    3. Find existing user by twitch_id; create new one if not found
    4. Issue JWT and redirect to frontend with ?token=<jwt>
    """
    token_data = await twitch_oauth.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for Twitch token",
        )

    twitch_access = token_data.get("access_token") or ""
    twitch_refresh = token_data.get("refresh_token") or ""

    user_info = await twitch_oauth.get_user_info(twitch_access)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Twitch",
        )

    twitch_id: str = user_info["id"]
    display_name: str = user_info["display_name"]

    # Look up existing user by Twitch ID
    result = await db.execute(select(User).where(User.twitch_id == twitch_id))
    user = result.scalar_one_or_none()

    if user is None:
        # First-time login — create the account using the Twitch display name as username.
        # If the username is already taken, append the Twitch ID to ensure uniqueness.
        username = display_name
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            username = f"{display_name}_{twitch_id}"

        user = User(
            username=username,
            role=UserRole.USER,
            twitch_id=twitch_id,
            twitch_username=display_name,
            twitch_access_token=twitch_access,
            twitch_refresh_token=twitch_refresh,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Returning user — refresh Twitch tokens and display name
        user.twitch_username = display_name
        user.twitch_access_token = twitch_access
        user.twitch_refresh_token = twitch_refresh
        await db.commit()

    # Import Twitch follows into user_streamers immediately after link (idempotent).
    try:
        added_follows = await sync_twitch_follows_for_user(db, user)
        await db.commit()
        if added_follows:
            logger.info(
                "Twitch OAuth: synced %s new follows for user_id=%s",
                added_follows,
                user.id,
            )
    except Exception as exc:
        logger.warning(
            "Twitch OAuth: follow sync failed for user_id=%s (login still succeeds): %s",
            user.id,
            exc,
            exc_info=True,
        )
        await db.rollback()

    jwt = create_access_token(data={"sub": str(user.id)})
    frontend_url = get_settings().frontend_url
    params = urlencode({"token": jwt})

    return RedirectResponse(url=f"{frontend_url}?{params}", status_code=302)
