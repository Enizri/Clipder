import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.endpoints import clips, leaderboard, admin, votes, health
from backend.api.v1.endpoints import auth, following, ai_chat, ai_editor
from backend.core.config import get_settings
from backend.core.database import init_database, shutdown_database
from backend.core.security import decode_token
from backend.core.state import ConnectionManager
from backend.core.tasks import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Clipder FastAPI server...")
    try:
        init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

    # Start background scheduler
    try:
        start_scheduler()
        logger.info("Background scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

    yield

    # Stop scheduler on shutdown
    try:
        stop_scheduler()
        logger.info("Background scheduler stopped")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")

    # Dispose DB connections on shutdown (important for reload)
    try:
        await shutdown_database()
        logger.info("Database engine disposed")
    except Exception as e:
        logger.warning(f"Database shutdown skipped: {e}")

    logger.info("Shutting down Clipder FastAPI server...")


app = FastAPI(
    title="Clipder API",
    description="Twitch clip curation and upload API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# Now add routes AFTER middleware
app.include_router(clips.router)
app.include_router(leaderboard.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(votes.router)
app.include_router(following.router)
app.include_router(ai_chat.router)
app.include_router(ai_editor.router)
app.include_router(health.router)


@app.websocket("/ws/leaderboard")
async def websocket_leaderboard(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
):
    """Real-time leaderboard updates. Accepts an optional JWT token for future
    authenticated-only features; connection is allowed without one."""
    if token is not None:
        payload = decode_token(token)
        if payload is None:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return

    ws_manager = ConnectionManager.get_instance()
    try:
        logger.info(f"WebSocket connect attempt from {websocket.client}")
        await ws_manager.connect(websocket)
        logger.info("✅ WebSocket connected successfully")
        try:
            while True:
                data = await websocket.receive_text()
                logger.debug(f"Received from websocket: {data}")
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected from {websocket.client}")
            ws_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error in websocket receive loop: {e}")
            ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Failed to accept websocket connection: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


@app.get("/")
async def root():
    return {"status": "ok", "app": "Clipder API", "version": "1.0.0"}


# Note: Detailed health checks at /api/v1/health, /api/v1/health/db, etc.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
