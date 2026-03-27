import base64
import json
import os
from typing import Dict, Any
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from backend.core.twitch_oauth import TwitchOAuth
from backend.models import User, UserRole, UserStreamer
from backend.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

twitch_oauth = TwitchOAuth()


def encode_state(user_id: int) -> str:
    return base64.b64encode(json.dumps({"user_id": user_id}).encode()).decode()


def decode_state(state: str) -> int | None:
    try:
        data = json.loads(base64.b64decode(state.encode()).decode())
        return data.get("user_id")
    except Exception:
        return None


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    twitch_id: str | None = None
    twitch_username: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TwitchLoginResponse(BaseModel):
    authorization_url: str


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    user = User(
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=UserRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token, user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token, user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.get("/twitch/login", response_model=TwitchLoginResponse)
async def twitch_login(current_user: User = Depends(get_current_user)):
    """Get Twitch OAuth authorization URL for the current logged-in user"""
    state = encode_state(current_user.id)
    auth_url = twitch_oauth.get_authorization_url(state)
    return TwitchLoginResponse(authorization_url=auth_url)


@router.get("/twitch/callback")
async def twitch_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Handle Twitch OAuth callback - links Twitch account to user"""
    user_id = decode_state(state)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Please try again.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found. Please login first.",
        )

    token_data = twitch_oauth.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token",
        )

    access_token = token_data.get("access_token") or ""
    refresh_token = token_data.get("refresh_token") or ""

    user_info = twitch_oauth.get_user_info(access_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Twitch",
        )

    user.twitch_id = user_info["id"]
    user.twitch_username = user_info["display_name"]
    user.twitch_access_token = access_token
    user.twitch_refresh_token = refresh_token
    await db.commit()

    # Build redirect URL using environment variable + URL encoding
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    params = urlencode({"twitch_linked": "true", "username": user_info["display_name"]})

    return RedirectResponse(url=f"{frontend_url}?{params}", status_code=302)


@router.post("/twitch/link")
async def link_twitch_account(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link Twitch account to existing user (user must be logged in)"""
    token_data = twitch_oauth.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token",
        )

    access_token = token_data.get("access_token") or ""
    refresh_token = token_data.get("refresh_token") or ""

    user_info = twitch_oauth.get_user_info(access_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Twitch",
        )

    current_user.twitch_id = user_info["id"]
    current_user.twitch_username = user_info["display_name"]
    current_user.twitch_access_token = access_token
    current_user.twitch_refresh_token = refresh_token
    await db.commit()
    await db.refresh(current_user)

    return {
        "status": "linked",
        "twitch_id": user_info["id"],
        "twitch_username": user_info["display_name"],
    }


@router.delete("/twitch/unlink")
async def unlink_twitch_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unlink Twitch account from user"""
    current_user.twitch_id = None
    current_user.twitch_username = None
    current_user.twitch_access_token = None
    current_user.twitch_refresh_token = None

    await db.execute(
        select(UserStreamer).where(UserStreamer.user_id == current_user.id)
    )
    await db.commit()

    return {"status": "unlinked"}
