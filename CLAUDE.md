# Clipder — Project Guide (CLAUDE.md)

> Single source of truth for architecture, conventions, and the active refactor plan.
> Every AI agent and human contributor must follow this document.

---
## Agent Persona:
You are a senior software architect with 20+ years of experience.
You write production-grade code, not tutorial code.
You always:
- Think about edge cases before writing
- Prefer simple solutions over clever ones
- Never leave broken or half-finished code
- Flag risks before implementing, don't just proceed
- Ask before making decisions that weren't explicitly planned
- add small comments to the code to explain the logic dont try to be clever just explain the logic

## 1. Project Overview

**Clipder** is a Twitch clip discovery and ranking platform. Users swipe through clips,
vote (like/dislike), and a real-time leaderboard tracks the top clips each month.

| Layer | Stack |
|-------|-------|
| Backend | FastAPI + Uvicorn (async), Python 3.12+ |
| Database | PostgreSQL (Supabase) via SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic (async mode) |
| Auth | JWT (HS256) + Bcrypt, Twitch OAuth |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Frontend | React 18 + TypeScript + Vite |
| Charting | Recharts |
| Routing | react-router-dom |
| Package Mgr | uv (Python), npm (Frontend) |

---

## 2. Directory Structure

```
ClipApp/
├── main.py                    # FastAPI entry point, router mounting, WebSocket, lifespan
├── pyproject.toml             # Python deps managed with uv
├── alembic.ini                # Migration config
├── AGENTS.md                  # Agent behavioral rules (immutable reference)
├── CLAUDE.md                  # THIS FILE — project guide
├── .env.example               # Required env vars template
├── .gitignore
├── LICENSE
├── README.md
│
├── alembic/
│   ├── env.py                 # Async migration runner
│   ├── script.py.mako
│   └── versions/              # Single consolidated migration
│
├── backend/
│   ├── __init__.py
│   ├── engine.py              # IMMUTABLE core engine (moved from root core.py)
│   │                          #   Config, TwitchClient, StateManager, GroqClient,
│   │                          #   VideoProcessor, YouTubeUploader, TikTokUploader
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── deps.py        # DI: get_db, get_current_user, check_pro, check_admin
│   │       └── endpoints/
│   │           ├── admin.py       # /api/v1/admin/*
│   │           ├── ai_chat.py     # /api/v1/ai/*
│   │           ├── ai_editor.py   # /api/v1/ai-editor/*
│   │           ├── auth.py        # /api/v1/auth/*
│   │           ├── clips.py       # /api/v1/clips/*
│   │           ├── following.py   # /api/v1/following/*
│   │           ├── health.py      # /api/v1/health/*
│   │           ├── leaderboard.py # /api/v1/leaderboard/*
│   │           └── votes.py       # /api/v1/votes/*
│   ├── core/
│   │   ├── config.py          # Pydantic Settings — ALL env vars live here
│   │   ├── security.py        # JWT + Bcrypt
│   │   ├── database.py        # Async engine + session (uses Settings)
│   │   ├── state.py           # ConnectionManager (WS) + AppState
│   │   ├── twitch_oauth.py    # Twitch OAuth helpers (async httpx)
│   │   ├── cache_provider.py  # LeaderboardCache ABC + DictLeaderboardCache
│   │   ├── tasks.py           # APScheduler background jobs
│   │   └── logger.py          # Logging config
│   ├── models/
│   │   ├── __init__.py        # Re-exports Base + all models
│   │   ├── user.py
│   │   ├── clip.py
│   │   ├── vote.py
│   │   ├── user_streamer.py
│   │   ├── user_clip_history.py
│   │   ├── clip_video_cache.py
│   │   ├── leaderboard_snapshot.py
│   │   └── leaderboard_monthly_summary.py
│   └── schemas/
│       ├── __init__.py
│       ├── auth.py
│       ├── clip.py
│       ├── clip_history.py
│       ├── admin.py
│       ├── leaderboard.py
│       └── vote.py
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx             # BrowserRouter + layout + <Routes>
│       ├── index.css
│       ├── types.ts            # Single source of truth for TS interfaces
│       ├── api/
│       │   └── client.ts       # Typed API client, all paths /api/v1/*
│       ├── pages/
│       │   ├── SwipePage.tsx
│       │   ├── LeaderboardPage.tsx
│       │   ├── AnalyticsPage.tsx
│       │   ├── AiEditorPage.tsx
│       │   └── ProfilePage.tsx
│       ├── components/
│       │   ├── SwipeStack.tsx
│       │   ├── AuthModal.tsx
│       │   ├── ProfilePanel.tsx
│       │   ├── CommentsPanel.tsx
│       │   ├── TheaterMode.tsx
│       │   ├── EmotePicker.tsx
│       │   ├── AiEditor.tsx
│       │   ├── Leaderboard.tsx
│       │   ├── AnalyticsDashboard.tsx
│       │   └── AnalyticsDashboard.css
│       └── hooks/
│           └── useLeaderboard.ts
│
├── scripts/
│   ├── db_maintenance/
│   │   ├── clean_history.py
│   │   └── cleanup_db.py
│   └── db_setup/
│       ├── create_admin_user.py
│       └── create_tables.py
│
├── tests/
│   ├── conftest.py
│   ├── integration/
│   ├── manual/
│   └── unit/
│
├── clips_to_process/          # Queue directory (runtime)
└── processed_clips/           # Archive directory (runtime)
```

---

## 3. Coding Conventions

### 3.1 Python (PEP 8 + project rules)

**Import ordering** — three groups separated by blank lines:
1. Standard library (`os`, `json`, `typing`, `datetime`, `pathlib`)
2. Third-party (`fastapi`, `pydantic`, `sqlalchemy`, `httpx`)
3. Local (`from backend.core.config import get_settings`)

**Naming:**

| Element | Style | Example |
|---------|-------|---------|
| Modules | snake_case | `clips.py` |
| Classes | PascalCase | `ClipResponse` |
| Functions | snake_case | `get_clips` |
| Constants | UPPER_SNAKE | `API_TIMEOUT = 30` |
| Private | _prefix | `_refresh_token` |

**Type hints** — mandatory on all function parameters and return types.
Use `Optional[X]` (not `X | None`) for compatibility.

**Pydantic** — use v2 API exclusively:
- `model_validate()` not `.from_orm()`
- `model_dump()` not `.dict()`
- `model_config = ConfigDict(from_attributes=True)` not `class Config`

**SQLAlchemy** — use 2.0 declarative style exclusively:
- `Mapped[str]` + `mapped_column()` everywhere
- Never use legacy `Column()` API
- `lazy="select"` on relationships (never `"selectin"`)

**Async** — every FastAPI handler and DB call is `async def`.
Never use sync `requests` in async code; use `httpx.AsyncClient` instead.

**Docstrings** — required on public classes and non-obvious endpoints.
Use Google-style (Args/Returns/Raises).

### 3.2 TypeScript / React

- Strict TypeScript (`strict: true` in tsconfig)
- All API response types defined once in `types.ts`
- No `any` — use proper interfaces
- Components are functional with hooks
- No inline styles for reusable patterns — use CSS classes
- No `console.log` in production code (use conditional `import.meta.env.DEV` guard if needed)
- Proper error handling — never `.catch(() => {})` silently

### 3.3 Comments

Comments explain **why**, not **what**. Do not narrate obvious code.
No emoji in code comments. No commented-out dead code.

---

## 4. Centralized Configuration

**Rule: Every environment variable is accessed through the `Settings` class.**

No module may call `os.getenv()` or `os.environ` directly.
The single exception is `alembic/env.py` (runs outside the app lifecycle).

### Settings class (`backend/core/config.py`)

```python
class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str                              # REQUIRED — no default

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # JWT — no weak defaults; app must fail loudly if unset
    secret_key: str                                # REQUIRED
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080       # 7 days

    # Twitch OAuth
    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    twitch_redirect_uri: str = "http://localhost:8000/api/v1/auth/twitch/callback"

    # Twitch content
    twitch_channels: str = ""                      # comma-separated
    twitch_categories: str = ""                    # comma-separated

    # Groq
    groq_api_key: str = ""

    # Opus Clip (optional)
    opus_clip_api_key: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"
```

Usage everywhere else:

```
from backend.core.config import get_settings

settings = get_settings()
url = settings.database_url
```

### Environment variables (`.env.example`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SECRET_KEY` | Yes | Strong random string for JWT signing |
| `TWITCH_CLIENT_ID` | Yes | From Twitch Developer Console |
| `TWITCH_CLIENT_SECRET` | Yes | From Twitch Developer Console |
| `GROQ_API_KEY` | Yes | For transcription/AI chat |
| `TWITCH_CHANNELS` | Yes | Comma-separated channel names |
| `TWITCH_CATEGORIES` | Yes | Comma-separated category names |
| `FRONTEND_URL` | No | CORS origin (default `http://localhost:3000`) |
| `ALGORITHM` | No | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | JWT TTL (default `10080`) |
| `SUPABASE_URL` | No | Supabase project URL |
| `SUPABASE_ANON_KEY` | No | Supabase anon key |
| `OPUS_CLIP_API_KEY` | No | Opus Clip integration |
| `VITE_API_ORIGIN` | No | Frontend-only: backend origin for cross-origin dev |

---

## 5. API Standards

### 5.1 All routes under `/api/v1/`

Every router uses the prefix `/api/v1/<resource>`. No exceptions.

| Router | Prefix | Auth |
|--------|--------|------|
| auth | `/api/v1/auth` | Public (register/login), JWT (me/twitch) |
| clips | `/api/v1/clips` | Public read, JWT for actions |
| votes | `/api/v1/votes` | JWT required |
| leaderboard | `/api/v1/leaderboard` | Public read |
| admin | `/api/v1/admin` | JWT + ADMIN role required |
| following | `/api/v1/following` | JWT required |
| ai_chat | `/api/v1/ai` | JWT required |
| ai_editor | `/api/v1/ai-editor` | JWT required |
| health | `/api/v1/health` | Public |

WebSocket: `/ws/leaderboard` (optional token auth)

### 5.2 Response format

- Success: return Pydantic `response_model` directly
- Error: raise `HTTPException(status_code=..., detail="...")`
- Lists: return empty list `[]`, never `None`
- Not found: `404` with descriptive detail

### 5.3 Frontend API client

All calls go through `frontend/src/api/client.ts` which:
- Prepends `/api/v1` to all paths
- Attaches `Authorization: Bearer <token>` for authenticated routes
- Parses error `detail` from FastAPI responses
- Never swallows errors silently

---

## 6. Security Rules

1. **NEVER** read, display, or commit `.env` files
2. **NEVER** hardcode API keys, secrets, or credentials in source code
3. **CORS**: use `FRONTEND_URL` env var for allowed origins — never `*` in production
4. **JWT**: `SECRET_KEY` is required with no fallback default — app refuses to start without it
5. **Admin routes**: require `ADMIN` role via `check_admin` dependency
6. **AI endpoints**: require authenticated user to prevent abuse
7. **SQL**: use ORM / parameterized queries exclusively — no string concatenation
8. **Passwords**: bcrypt hashing via `backend/core/security.py`
9. **Async safety**: never use sync `requests` in async handlers — use `httpx.AsyncClient`
10. **WebSocket**: validate JWT token on connection when sensitive data is involved

---

## 7. Database Rules

- **ORM**: SQLAlchemy 2.0 declarative (`Mapped` / `mapped_column`) exclusively
- **Migrations**: Alembic async mode; one clean migration chain
- **Supabase pooler**: when `"pooler"` appears in URL, use `ssl=require` + `statement_cache_size=0`
- **Sessions**: async sessions via `get_db()` dependency injection
- **Relationships**: `lazy="select"` (load on access, not on every query)
- **IDs**: integer auto-increment primary keys
- **Timestamps**: `DateTime(timezone=True)` with `func.now()` server defaults

---

## 8. Immutable Engine (`backend/engine.py`)

This file (originally `core.py`) contains the algorithmic core:
`Config`, `TwitchClient`, `CaptionGenerator`, `GroqClient`, `VideoProcessor`,
`YouTubeUploader`, `TikTokUploader`, `StateManager`, `ClipBot`.

**DO NOT modify its logic or function signatures.**
It has its own `Config.from_env()` dataclass — that is the one exception to the
centralized Settings rule, because it predates the FastAPI backend.

The FastAPI `AppState` in `backend/core/state.py` wraps this engine and
bridges it to the async web layer.

---

## 9. Refactor Plan — Chunk Order

This project is undergoing a full reset. Work proceeds in 7 sequential chunks.

### Chunk 1: File Cleanup + CLAUDE.md
- Delete redundant files (see list below)
- Move `core.py` to `backend/engine.py` (update imports)
- Generate this CLAUDE.md
- Update AGENTS.md path references

**Files to delete:**
- `EprojectsClipAppREADME_CURRENT_STATUS.txt`
- `FINAL_STATUS.md`
- `CONTRIBUTING.md`
- `verify_fixes.sh`
- `docs/archive/` (entire directory)
- `backend/CLAUDE.md`
- `frontend/CLAUDE.md`
- `tests/manual/test_phase4.sh`
- `tests/manual/test_phase4.ps1`
- `scripts/manual_test_workflow.py`

### Chunk 2: Backend Critical Fixes + Centralized Config
- Expand `Settings` class to own ALL env vars
- Refactor every module to use `get_settings()` (zero `os.getenv` in backend)
- Fix broken import in `ai_editor.py`
- Fix `_upsert_clips` missing `month_key`
- Fix `job_finalize_month_end` missing `total_unique_voters`
- Fix inconsistent leaderboard scoring
- Remove dead imports
- Convert `user_clip_history.py` to `Mapped` style
- Replace `.dict()` with `.model_dump()`
- Standardize `Optional[X]` and import ordering

### Chunk 3: API Route Normalization
- Standardize all router prefixes to `/api/v1/*`
- Update `main.py` router mounting
- Update Vite proxy config
- Update `client.ts` to match new paths
- Remove obsolete `createLeaderboardSocket`

### Chunk 4: Security Hardening
- Auth guards on admin endpoints (ADMIN role)
- Auth guard on AI chat (authenticated user)
- CORS restricted to `FRONTEND_URL`
- Remove Giphy feature entirely
- Remove JWT weak default — fail if `SECRET_KEY` missing
- Convert `twitch_oauth.py` to async `httpx`
- Optional WebSocket token auth

### Chunk 5: Database Fresh Start
- Delete all files in `alembic/versions/`
- Drop `LeaderboardClipPerformance` model (unused)
- Add `month_key` server default to `Clip`
- Fix `alembic/env.py` env loading and URL default
- Ensure all models use `Mapped` style
- Generate single fresh consolidated migration

### Chunk 6: Frontend Restructure
- Add `react-router-dom` for page-based routing
- Add ESLint to `devDependencies`
- Create `pages/` directory with routed page components
- Extract components from `App.tsx` god component
- Remove Giphy UI code
- Consolidate types in `types.ts`
- Fix error handling (no silent `.catch`)
- Remove verbose `console.log`

### Chunk 7: Sync Verification + Finalization ✅ COMPLETE
- Verified every frontend API call matches a backend route
- Verified Pydantic schemas match TypeScript types
- Fixed `client.ts` auth header guard — added `/ai-editor` and `/auth/twitch` paths
- Fixed `client.ts` `getLeaderboard()` — now calls `/leaderboard/current` with correct return type
- Fixed `auth.py` `/twitch/link` — now accepts JSON body via `TwitchLinkRequest` model
- Fixed `ai_editor.py` — moved `DELETE /history/clear-all` before `DELETE /history/{history_id}`
- Fixed `ClipHistoryResponse.updated_at` — now `Optional[datetime]` matching the nullable model column
- Moved `pytest`, `pytest-asyncio`, `aiosqlite` from main deps to `[dependency-groups] dev`
- Added `ruff` to dev dependencies; ran `uv run ruff check --fix` on all backend files
- Ran `npx tsc --noEmit` and `npx eslint` — both pass with zero errors

---

## 10. Key Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | Fresh consolidated migration | Supabase DB has no important data |
| Frontend routing | `react-router-dom` | Proper page-based navigation |
| Leaderboard hourly aggregates | Dropped | No model or code uses it |
| Giphy feature | Removed entirely | Hardcoded API key, low value |
| Env var access | Centralized `Settings` class | No scattered `os.getenv()` |
| `core.py` location | Moved to `backend/engine.py` | Clean project root |
| API prefix | All routes under `/api/v1/*` | Consistency |
| SQLAlchemy style | `Mapped` / `mapped_column` only | No legacy `Column` API |
| Sync HTTP calls | Replaced with `httpx` async | Never block the event loop |
| FastAPI route order | Static paths before dynamic `{param}` segments | Prevents path shadowing (e.g. `/clear-all` vs `/{id}`) |
| Auth guard list | `requiresAuth` in `client.ts` — include every authenticated prefix | Forgetting a prefix silently drops the JWT header |

---

## 11. Build & Run

```bash
# Install Python deps
uv sync

# Install frontend deps
cd frontend && npm install

# Run backend (from project root)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run frontend (from frontend/)
npm run dev

# Run migrations
alembic upgrade head

# Run tests
pytest
```

### Adding dependencies

```bash
# Python — NEVER use pip
uv add <package>

# Frontend
cd frontend && npm install <package>
```
