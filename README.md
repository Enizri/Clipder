# Clipder Pro

A modern Twitch clip discovery and curation platform with card-swipe swiping.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)

## Features

- **Swipe & Vote**: card-swipe interface for discovering Twitch clips
- **Video Preview**: Hover to preview clips with volume controls
- **Theater Mode**: Full-screen video viewing experience
- **Comments**: Real-time comments with Twitch emote support
- **Leaderboard**: Track your most liked clips
- **Admin Queue**: Manage clips ready for upload
- **Multi-Platform**: Twitch, TikTok, YouTube support

## Tech Stack

- **Backend**: FastAPI + Python 3.12+
- **Frontend**: React + TypeScript + Vite
- **Package Management**: uv (Python), npm (Node)

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Twitch API credentials
- FFmpeg (for video processing)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ClipApp.git
cd ClipApp
```

2. **Set up Python environment**
```bash
uv sync
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Set up frontend**
```bash
cd frontend
npm install
```

### Running the Application

**Backend (Terminal 1)**
```bash
uv run uvicorn main:app --reload --port 8000
```

**Frontend (Terminal 2)**
```bash
cd frontend
npm run dev
```

**Or use the startup script**
```bash
./start.bat  # Windows
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TWITCH_CLIENT_ID` | Yes | Twitch OAuth client ID |
| `TWITCH_CLIENT_SECRET` | Yes | Twitch OAuth client secret |
| `GROQ_API_KEY` | Yes | Groq API key for transcription |
| `TWITCH_CHANNELS` | Yes | Comma-separated channel names |
| `TWITCH_CATEGORIES` | Yes | Comma-separated Twitch category names |
| `OPUS_CLIP_API_KEY` | No | Opus Clip API key |

## Project Structure

```
ClipApp/
├── backend/              # FastAPI backend
│   ├── api/v1/         # API endpoints
│   │   └── endpoints/  # Route handlers
│   ├── core/           # Core utilities
│   └── schemas/        # Pydantic models
├── frontend/           # React frontend
│   ├── src/
│   │   ├── api/       # API client
│   │   ├── components/# React components
│   │   └── hooks/     # Custom hooks
│   └── dist/           # Production build
├── core.py             # Core business logic
└── main.py             # FastAPI entry point
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/clips` | Get clips by category |
| GET | `/api/categories` | Get available categories |
| GET | `/api/clip/{id}/video-url` | Get clip video URL |
| POST | `/api/clip/{id}/action` | Like/dislike a clip |
| GET | `/api/leaderboard` | Get liked clips |
| GET | `/api/emotes` | Get available emotes |
| GET | `/api/gifs` | Search GIFs |

## Versioning

- `v1.0.0` - Original Flask version
- `v2.0.0` - FastAPI + React refactor

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for details.
