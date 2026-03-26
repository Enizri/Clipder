# Clipder - Agent Guidelines

## Role & Task

```
Role: Senior Full-Stack Engineer (20+ Years Exp)
Task: Refactor ClipApp to FastAPI + React/TS/Vite
```

---

## 0. Environment & Dependency Rules (CRITICAL)

- **Project Manager:** This project is already initialized with `uv`.
- **NO PIP:** You are **strictly forbidden** from using `pip install`.
- **Auto-Update:** For every new library needed (FastAPI, Uvicorn, Pydantic, React, etc.), you **MUST** execute `uv add [package]`.
- **Sync:** Ensure `pyproject.toml` and `uv.lock` are always updated **before** writing corresponding code.

### Current Major Dependencies
- **Backend:** FastAPI (0.135.2+), Uvicorn, SQLAlchemy[asyncio] (2.0.48+), asyncpg (0.31.0+), Alembic (1.18.4+)
- **Auth:** python-jose[cryptography], bcrypt (5.0.0+), email-validator
- **Database:** PostgreSQL-compatible via asyncpg + sqlalchemy
- **API Tools:** httpx, pydantic-settings, pydantic (2.12.5+)
- **Video Processing:** moviepy, yt-dlp, tiktok-uploader, numpy
- **Data:** requests, python-dotenv
- **Frontend:** React, TypeScript, Vite (in frontend/ directory)

---

## 1. Core Constraints (DO NOT BREAK)

- **Immutable Core:** `core.py` contains the algorithmic engine (Config, TwitchClient, StateManager, GroqClient, VideoProcessor, YouTubeUploader, TikTokUploader). **DO NOT modify** its logic or function signatures. It is the "Source of Truth."
- **Dependency Management:** Use `uv`. Every new dependency **MUST** be added via `uv add`. Update `pyproject.toml` accordingly.
- **State Integrity:** Use `ConnectionManager` singleton in `backend/core/state.py` for WebSocket broadcasting. FastAPI routes access `core.py`'s StateManager via dependency injection. Ensure state is thread-safe and shared across all route handlers.
- **Database:** PostgreSQL with SQLAlchemy async ORM. Use Alembic for migrations. Environment variable `DATABASE_URL` required (e.g., `postgresql+asyncpg://user:pass@localhost/clipder`).

---

## 2. Technical Stack

- **Backend:** FastAPI with Uvicorn + async handlers. Use `APIRouter` for modularity.
- **Database:** PostgreSQL with SQLAlchemy async ORM + asyncpg driver. Alembic for schema migrations.
- **Frontend:** React + TypeScript + Vite. Located in `frontend/` directory.
- **Communication:** Pure JSON API over HTTP/WebSocket. No Jinja2/HTML templates.
- **Authentication:** JWT (HS256) + Bcrypt hashing. Twitch OAuth for social login.
- **Real-time:** WebSocket support via FastAPI for leaderboard streaming (ConnectionManager singleton).
- **Performance:** All endpoints are `async def`. Use SQLAlchemy async sessions with dependency injection.
- **Video Processing:** Integrates with `core.py` for clip extraction, transcription (via Groq), and multi-platform uploads (YouTube, TikTok).

---

## 3. Actual Directory Structure (CURRENT)

```
ClipApp/
├── pyproject.toml                # Dependencies managed with uv
├── core.py                       # IMMUTABLE: Core engine (TwitchClient, StateManager, etc.)
├── main.py                       # FastAPI entry point with 7 routers + WebSocket
├── alembic.ini                   # Database migration config
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                 # Migration scripts (e.g., b7f027ceb621_initial_migration.py)
├── backend/
│   ├── __init__.py
│   ├── api/
│   │   └── v1/
│   │       ├── deps.py          # Dependency injection (is_pro, get_current_user, etc.)
│   │       └── endpoints/
│   │           ├── auth.py      # Login/Register/Twitch OAuth callback
│   │           ├── clips.py     # Swipe & Like logic
│   │           ├── leaderboard.py # Top 10 Monthly, WebSocket broadcast
│   │           ├── vote.py      # Vote endpoints
│   │           ├── admin.py     # Pro Playground & Admin queue
│   │           ├── following.py # Following management
│   │           └── ai_chat.py   # AI chat/transcription endpoints
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (Twitch OAuth, Supabase, JWT settings)
│   │   ├── security.py          # JWT & Bcrypt hashing logic
│   │   ├── database.py          # SQLAlchemy async engine & session setup
│   │   ├── state.py             # ConnectionManager singleton for WebSocket broadcasting
│   │   └── twitch_oauth.py      # Twitch OAuth flow helpers
│   ├── models/
│   │   ├── user.py              # User model with UserRole enum (USER, PRO, ADMIN)
│   │   ├── clip.py              # Clip model with month_key & score fields
│   │   ├── vote.py              # Vote model (user-clip relations)
│   │   └── user_streamer.py     # UserStreamer model (following relationships)
│   └── schemas/
│       ├── admin.py             # Admin Pydantic schemas
│       ├── clip.py              # Clip response/request schemas
│       └── leaderboard.py       # Leaderboard response schemas
├── frontend/                     # React/TS + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── types.ts             # TypeScript types matching Pydantic schemas
│   │   ├── api/client.ts        # API client utility
│   │   ├── components/          # React components
│   │   └── hooks/               # Custom React hooks
│   ├── package.json
│   ├── vite.config.ts
│   └── index.html
├── clips_to_process/            # Queue for clips awaiting processing
├── processed_clips/             # Archived processed clips
└── .env                         # Environment variables (DO NOT COMMIT)
```

## 4. Execution Protocol

1. **Validation:** For every file change, run a syntax check.
2. **Sync Check:** Ensure Frontend API calls match Backend Pydantic schemas exactly.
3. **Regression Test:** After refactoring a route (e.g., `/api/clips`), verify data returned matches legacy Flask output.
4. **No Ghost Code:** Remove all Flask-specific code (`app.route`, `render_template`) once FastAPI equivalent is stable.
5. **No Repeated Code:** Do not rewrite the same code twice if there are no changes. Copy-paste or leave as-is if it works.

---

## 5. Zero-Lag Mandate

- Convert all synchronous Flask calls to `async def` in FastAPI.
- Use **Pydantic Schemas** in `backend/schemas/` to define data contracts. Frontend and Backend must be 100% in sync with 0 runtime type bugs.
- Optimize state management in `state.py` for FastAPI concurrency. Suggest optimizations before implementing.

---

## 5.5 Current API Endpoints (7 Routers)

| Module | Endpoint Route | Purpose |
|--------|---|---------|
| **auth.py** | `/api/v1/auth/*` | Login, register, Twitch OAuth callback, token validation |
| **clips.py** | `/api/v1/clips/*` | Get clips, swipe/like interactions, clip details |
| **leaderboard.py** | `/api/v1/leaderboard/*` | Top 10 monthly clips with WebSocket broadcasting |
| **votes.py** | `/api/v1/votes/*` | User vote management (like/unlike clips) |
| **admin.py** | `/api/v1/admin/*` | Pro playlist upload, admin queue, category management |
| **following.py** | `/api/v1/following/*` | Add/remove followed streamers |
| **ai_chat.py** | `/api/v1/ai/*` | AI transcription, chat endpoints |

### WebSocket Endpoint
- **`/ws/leaderboard`** – Real-time leaderboard updates via `ConnectionManager.broadcast()` singleton

---

## 5.6 Database Models (SQLAlchemy ORM)

**User Model:**
- id (PK), username, email, password_hash
- role (Enum: USER, PRO, ADMIN)
- twitch_id, twitch_username, twitch_access_token, twitch_refresh_token
- created_at

**Clip Model:**
- id (PK), twitch_clip_id (unique), title, url, thumbnail_url
- view_count (BigInteger), creator_name
- month_key (indexed, format: "YYYY-MM"), score (Float)
- created_at

**Vote Model:**
- id (PK), user_id (FK), clip_id (FK)
- vote_type (e.g., "like", "unlike")
- created_at
- Relationship to User & Clip with cascade delete

**UserStreamer Model:**
- id (PK), user_id (FK), streamer_name, twitch_channel_id
- Relationship to User with cascade delete

---

## 6. Testing Requirement

Before considering a file "Done," verify the new FastAPI endpoint returns the **exact same data structure** as the original Flask version. Ensure `core.py` integration remains seamless.

---

## Code Style Guidelines

### Python Version
- **Minimum:** Python 3.12
- **Package Manager:** uv ONLY (no pip)

### Imports
Organize imports in three groups with blank lines between:
1. Standard library (`os`, `json`, `pathlib`, `typing`, `asyncio`)
2. Third-party packages (`fastapi`, `uvicorn`, `pydantic`, `requests`)
3. Local modules (`from backend.core import ...`, `from .schemas import ...`)

```python
# Correct ordering
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from asyncio import Lock

import requests
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core.config import get_settings
from backend.schemas.clip import ClipResponse
```

### Naming Conventions
| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `clips.py`, `state.py` |
| Classes | PascalCase | `ClipResponse`, `StateManager` |
| Functions | snake_case | `get_clips`, `fetch_clips_for_category` |
| Variables | snake_case | `clip_scores`, `admin_upload_queue` |
| Constants | UPPER_SNAKE | `API_TIMEOUT = 30` |
| Private methods | _prefix | `_refresh_token`, `_save` |
| Pydantic models | PascalCase + suffix | `ClipResponse`, `ClipCreate` |

### Type Hints
- **Always use type hints** for function parameters and return types
- Use `Optional[X]` instead of `X | None` for compatibility
- Use `Dict`, `List`, `Any` from `typing`
- Pydantic models handle request/response validation

```python
# FastAPI route with types
async def get_clips(category: str = "My Streamers") -> List[ClipResponse]:
    ...

# Pydantic schema
class ClipResponse(BaseModel):
    id: str
    title: str
    url: str
    view_count: int
    creator_name: str
    local_likes: int = 0
    comment_count: int = 0

    class Config:
        from_attributes = True
```

### Docstrings
Use docstrings for:
- All public classes
- Public methods with non-obvious behavior
- FastAPI endpoints (brief description)

```python
async def get_clip_video_url(clip_id: str) -> dict:
    """Fetch the direct video URL for a clip.
    
    Args:
        clip_id: Unique Twitch clip identifier
        
    Returns:
        Dict with video_url and title
        
    Raises:
        HTTPException: 404 if clip not found
    """
```

### Data Classes & Pydantic Models
Use `@dataclass` for simple data containers. Use Pydantic `BaseModel` for API schemas:

```python
from pydantic import BaseModel, Field
from dataclasses import dataclass

# Pydantic for API (preferred)
class ClipCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    url: str
    view_count: int = 0

# Dataclass for internal config
@dataclass
class AppConfig:
    twitch_client_id: str
    twitch_client_secret: str
    base_dir: Path
```

### FastAPI Patterns

```python
# Router definition
api_router = APIRouter(prefix="/api/v1", tags=["clips"])

# Dependency injection for state
async def get_state() -> StateManager:
    return StateManager.get_instance()

# Route with dependency
@api_router.get("/clips", response_model=List[ClipResponse])
async def get_clips(
    category: str = "My Streamers",
    state: StateManager = Depends(get_state)
) -> List[ClipResponse]:
    clips = await state.fetch_clips(category)
    return clips

# Error handling
@api_router.get("/clips/{clip_id}")
async def get_clip(clip_id: str, state: StateManager = Depends(get_state)):
    clip = await state.get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return clip
```

### Error Handling
- Use `HTTPException` for FastAPI route errors
- Log errors with context using the logger
- Return empty collections (not `None`) for list operations
- Use `Optional` return type for values that may not exist

```python
async def get_recent_clips(broadcaster_id: str) -> List[Dict[str, Any]]:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        logger.error(f"Error fetching clips: {e}")
        return []

async def get_broadcaster_id(username: str) -> Optional[str]:
    try:
        ...
        return data[0]["id"] if data else None
    except Exception as e:
        logger.error(f"Error fetching broadcaster ID: {e}")
        return None
```

### Logging
Use the standard `logging` module. Configure at module level:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing clip: %s", clip_id)
logger.error("Failed to upload: %s", error)
```

### Constants & Magic Numbers
Define meaningful constants at module or class level:

```python
# At module level
DEFAULT_TIMEOUT = 10
MAX_CLIPS_PER_CHANNEL = 10
SWIPE_THRESHOLD = 100

# At class level
class TwitchClient:
    API_BASE = "https://api.twitch.tv/helix"
    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
```

### Section Headers
Use consistent section dividers in large files:
```python
# ==============================================================================
# CONFIGURATION & LOGGING
# ==============================================================================

# ==============================================================================
# TWITCH CLIENT
# ==============================================================================
```

---

## Security (CRITICAL)

- **NEVER read, display, or expose `.env` files** - They contain sensitive API keys and credentials
- **ONLY read `.env.example`** to understand required environment variables
- If asked to work with credentials, use placeholder values and instruct user to add their own
- If credentials are accidentally exposed in conversation, warn the user to rotate them immediately

### Accessing Environment Variables in Code

When you need to access environment variables in Python code (for API calls, configs, etc.), use `os.environ` or `python-dotenv`. **Never hardcode credentials** - always load them from environment:

```python
import os
from dotenv import load_dotenv

# Load .env file (this only reads, never exposes to user)
load_dotenv()

# Access credentials safely - they go directly to the API/library, never exposed in output
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
```

The application should already have `python-dotenv` in its dependencies via `core.py` - use `Config.from_env()` which handles this automatically.

---

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@localhost:5432/clipder` |
| `TWITCH_CLIENT_ID` | Yes | Twitch OAuth client ID | From Twitch Developer Console |
| `TWITCH_CLIENT_SECRET` | Yes | Twitch OAuth client secret | From Twitch Developer Console |
| `TWITCH_REDIRECT_URI` | Yes | OAuth redirect URL | `http://localhost:8000/auth/twitch/callback` |
| `GROQ_API_KEY` | Yes | Groq API key for transcription/AI | From Groq Console |
| `TWITCH_CHANNELS` | Yes | Comma-separated channel names | `channel1,channel2,channel3` |
| `TWITCH_CATEGORIES` | Yes | Comma-separated Twitch category names | `Just Chatting,Valorant,Minecraft` |
| `SECRET_KEY` | Yes | JWT signing secret (change in production) | Any strong random string |
| `ALGORITHM` | No | JWT algorithm | `HS256` (default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT expiration time | `10080` (7 days, default) |
| `OPUS_CLIP_API_KEY` | No | Opus Clip API key (enables Opus features) | From Opus Clip |
| `SUPABASE_URL` | No | Supabase project URL (if using Supabase) | From Supabase dashboard |
| `SUPABASE_ANON_KEY` | No | Supabase anonymous key | From Supabase dashboard |

---

## Common Tasks

### Adding a new API endpoint
1. Create Pydantic schema in `backend/schemas/`
2. Add route in appropriate `backend/api/v1/endpoints/*.py`
3. Use `APIRouter` for grouping
4. Return Pydantic model with `response_model=`
5. Add to main.py router

### Adding a new frontend component
1. Create component in `frontend/src/components/`
2. Use TypeScript types matching Pydantic schemas
3. Call API via typed fetch/axios utility
4. Handle loading/error states properly

### Adding a new dependency
1. Run `uv add [package]`
2. Verify `pyproject.toml` and `uv.lock` updated
3. Import and use in code
4. Update AGENTS.md if adding new conventions

---

## Build & Run Commands

### Package Management (uv)
```bash
# Install dependencies
uv sync

# Add a new dependency
uv add [package]

# Add dev dependency
uv add --dev pytest pytest-cov

# Remove a dependency
uv remove [package]

# Update lock file
uv lock
```

### Running the Application
```bash
# Run FastAPI backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run frontend (in frontend/ directory)
npm run dev

# Run both concurrently (recommended)
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Linting & Type Checking
```bash
# Run ruff linter
ruff check .

# Auto-fix with ruff
ruff check --fix .

# Run type checker
mypy .

# Run specific file
ruff check backend/
mypy main.py
```
