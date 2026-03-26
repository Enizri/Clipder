import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.endpoints import clips, leaderboard, admin, votes
from backend.api.v1.endpoints import auth, following, ai_chat, ai_editor
from backend.core.database import init_database
from backend.core.state import ConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Clipder FastAPI server...")
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    yield
    logger.info("Shutting down Clipder FastAPI server...")


app = FastAPI(
    title="Clipder API",
    description="Twitch clip curation and upload API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clips.router)
app.include_router(leaderboard.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(votes.router)
app.include_router(following.router)
app.include_router(ai_chat.router)
app.include_router(ai_editor.router)


@app.websocket("/ws/leaderboard")
async def websocket_leaderboard(websocket: WebSocket):
    ws_manager = ConnectionManager.get_instance()
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/")
async def root():
    return {"status": "ok", "app": "Clipder API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
