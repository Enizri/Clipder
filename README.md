# Clipder

Twitch clip discovery: swipe to vote, rank a live monthly leaderboard, then
send liked clips through Groq (transcript + score) and queue them for
YouTube Shorts and TikTok.

![Demo: swipe a Twitch clip, open the queue, analyze, upload to YouTube Shorts and TikTok](docs/screenshots/clipder-demo.gif)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-green.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)

**Repo:** [github.com/Enizri/Clipder](https://github.com/Enizri/Clipder)

### Resume (two lines)

Clipder — FastAPI + React app for Twitch clip discovery: swipe to vote, live monthly leaderboard, and a playground that transcribes liked clips with Groq then queues YouTube Shorts and TikTok.
https://github.com/Enizri/Clipder

YouTube / TikTok **publish** is a queued export (live adapters are stubs). The
playground still runs Groq analysis when `GROQ_API_KEY` is set.

## Features

- **Swipe & Vote** — card-swipe interface for discovering Twitch clips
- **Playground** — swipe right to queue a clip, run Groq analysis (transcript / score / title), then queue YouTube Shorts + TikTok
- **Demo mode** — `http://localhost:3000/?demo=1` walks that flow on public Twitch clips (no login)
- **Video Preview** — Hover-to-preview with volume controls
- **Theater Mode** — Full-screen viewing experience
- **Comments** — Real-time clip comments with Twitch emote support
- **Leaderboard** — Monthly ranked clips with live WebSocket updates
- **Analytics** — Visual dashboards with Recharts
- **Admin Queue** — Admin-only process endpoints
- **Twitch OAuth** — Link your Twitch account, sync followed channels

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn (async), Python 3.12+ |
| Database | PostgreSQL via SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic (async mode) |
| Auth | JWT (HS256) + Bcrypt, Twitch OAuth |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Frontend | React 18 + TypeScript + Vite |
| Charting | Recharts |
| Routing | react-router-dom |
| Package Mgr | uv (Python), npm (Frontend) |

---

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** (with npm)
- **uv** — Python package manager ([install guide](https://docs.astral.sh/uv/getting-started/installation/))
- **PostgreSQL** — local instance or hosted (e.g. Supabase)
- **Twitch Developer App** — for API credentials ([dev.twitch.tv](https://dev.twitch.tv/console/apps))

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Enizri/Clipder.git
cd Clipder
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials. At minimum you need:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql+asyncpg://user:pass@localhost:5432/clipder` |
| `SECRET_KEY` | A strong random string for JWT signing (the app refuses to start without it) |
| `TWITCH_CLIENT_ID` | From your Twitch Developer Console app |
| `TWITCH_CLIENT_SECRET` | From your Twitch Developer Console app |
| `GROQ_API_KEY` | From [console.groq.com](https://console.groq.com) — used for AI transcription/chat |
| `TWITCH_CHANNELS` | Comma-separated Twitch channel names to fetch clips from |
| `TWITCH_CATEGORIES` | Comma-separated Twitch category names (e.g. `Just Chatting,VALORANT`) |

See `.env.example` for the full list of optional variables.

### 3. Install Python dependencies

```bash
uv sync
```

This installs everything listed in `pyproject.toml` and locks versions in `uv.lock`.

### 4. Run database migrations

Make sure your PostgreSQL database exists and `DATABASE_URL` in `.env` points to it, then:

```bash
uv run alembic upgrade head
```

This creates all the tables (users, clips, votes, leaderboard, etc.).

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

The `package-lock.json` is committed, so `npm install` will produce a
deterministic, reproducible `node_modules`.

### 6. Start the application

**Backend** (from project root):

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (from `frontend/`):

```bash
cd frontend
npm run dev
```

The Vite dev server starts on **http://localhost:3000** and automatically
proxies `/api/*` and `/ws/*` requests to the backend at `localhost:8000`
(configured in `vite.config.ts`). Open **http://localhost:3000** in your
browser.

Login-free product walkthrough (public Twitch clips, local queue only):

**http://localhost:3000/?demo=1**

---

## Project Structure

```
Clipder/
├── main.py                    # FastAPI entry point, router mounting, WebSocket, lifespan
├── pyproject.toml             # Python deps (managed with uv)
├── uv.lock                    # Locked Python dependency versions
├── alembic.ini                # Migration config
├── .env.example               # Required env vars template
├── CLAUDE.md                  # Project guide & conventions
├── AGENTS.md                  # Agent behavioral rules
│
├── alembic/
│   ├── env.py                 # Async migration runner
│   └── versions/              # Migration scripts
│
├── backend/
│   ├── engine.py              # Core engine (TwitchClient, VideoProcessor, etc.)
│   ├── api/v1/
│   │   ├── deps.py            # DI: get_db, get_current_user, check_admin
│   │   └── endpoints/
│   │       ├── admin.py       # /api/v1/admin/*
│   │       ├── ai_chat.py     # /api/v1/ai/*
│   │       ├── ai_editor.py   # /api/v1/ai-editor/*
│   │       ├── auth.py        # /api/v1/auth/*
│   │       ├── clips.py       # /api/v1/clips/*
│   │       ├── following.py   # /api/v1/following/*
│   │       ├── health.py      # /api/v1/health/*
│   │       ├── leaderboard.py # /api/v1/leaderboard/*
│   │       └── votes.py       # /api/v1/votes/*
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (all env vars)
│   │   ├── security.py        # JWT + Bcrypt
│   │   ├── database.py        # Async engine + session factory
│   │   ├── state.py           # ConnectionManager (WebSocket)
│   │   ├── tasks.py           # APScheduler background jobs
│   │   ├── cache_provider.py  # Leaderboard cache
│   │   ├── twitch_oauth.py    # Twitch OAuth helpers (httpx)
│   │   └── logger.py          # Logging config
│   ├── models/                # SQLAlchemy ORM models
│   └── schemas/               # Pydantic request/response schemas
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json      # Locked frontend deps for reproducible installs
│   ├── tsconfig.json
│   ├── vite.config.ts         # Dev server + proxy config
│   ├── eslint.config.js
│   ├── .env.example           # Frontend env var template
│   └── src/
│       ├── main.tsx           # React entry point
│       ├── App.tsx            # BrowserRouter + layout + routes
│       ├── index.css          # Global styles
│       ├── types.ts           # Shared TypeScript interfaces
│       ├── api/client.ts      # Typed API client (all /api/v1/* calls)
│       ├── pages/             # Route-level page components
│       ├── components/        # Reusable UI components
│       └── hooks/             # Custom React hooks
│
└── scripts/                   # DB maintenance & setup utilities
```

---

## API Endpoints

All routes live under `/api/v1/`. The backend exposes these router groups:

| Router | Prefix | Auth |
|--------|--------|------|
| auth | `/api/v1/auth` | Public (Twitch OAuth), JWT (`/me`) |
| clips | `/api/v1/clips` | Public |
| votes | `/api/v1/votes` | JWT required |
| leaderboard | `/api/v1/leaderboard` | Public |
| following | `/api/v1/following` | JWT required |
| admin | `/api/v1/admin` | JWT + ADMIN role |
| ai_chat | `/api/v1/ai` | JWT required |
| ai_editor | `/api/v1/ai-editor` | JWT required |
| health | `/api/v1/health` | Public |

**WebSocket:** `ws://localhost:8000/ws/leaderboard` — real-time leaderboard updates.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | — | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SECRET_KEY` | **Yes** | — | Strong random string for JWT signing |
| `TWITCH_CLIENT_ID` | **Yes** | — | Twitch OAuth client ID |
| `TWITCH_CLIENT_SECRET` | **Yes** | — | Twitch OAuth client secret |
| `GROQ_API_KEY` | **Yes** | — | Groq API key for AI features |
| `GROQ_CHAT_MODEL` | No | `llama-3.3-70b-versatile` | Groq cloud chat model (playground). Not a local LLM. |
| `TWITCH_CHANNELS` | **Yes** | — | Comma-separated channel names |
| `TWITCH_CATEGORIES` | **Yes** | — | Comma-separated category names |
| `FRONTEND_URL` | No | `http://localhost:3000` | CORS allowed origin |
| `TWITCH_REDIRECT_URI` | No | `http://localhost:8000/api/v1/auth/twitch/callback` | OAuth callback URL |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `10080` | JWT TTL (7 days) |
| `SUPABASE_URL` | No | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | No | — | Supabase anonymous key |
| `OPUS_CLIP_API_KEY` | No | — | Opus Clip integration |

The frontend has one optional variable in `frontend/.env`:

| Variable | Description |
|----------|-------------|
| `VITE_API_ORIGIN` | Set only if the backend runs on a different host. Leave empty for local dev (Vite proxy handles it). |

---

## Development

```bash
# Lint Python
uv run ruff check .

# Auto-fix Python lint
uv run ruff check --fix .

# Lint frontend
cd frontend && npx eslint .

# Type-check frontend
cd frontend && npx tsc --noEmit

# Run tests
uv run pytest
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
