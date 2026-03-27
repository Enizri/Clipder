import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.api.v1.endpoints import clips, leaderboard, admin, votes, health
from backend.api.v1.endpoints import auth, following, ai_chat, ai_editor
from backend.core.database import init_database
from backend.core.state import ConnectionManager
from backend.core.tasks import start_scheduler, stop_scheduler
from backend.core import logger as core_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# CORS GUARANTEE MIDDLEWARE - Ensures CORS headers even on error responses
# ==============================================================================
class CORSGuaranteeMiddleware(BaseHTTPMiddleware):
    """Ensure CORS headers are present on ALL responses, including errors."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Add CORS headers to every response
        response.headers["access-control-allow-origin"] = "*"
        response.headers["access-control-allow-methods"] = "*"
        response.headers["access-control-allow-headers"] = "*"
        response.headers["access-control-expose-headers"] = "*"
        return response


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

    logger.info("Shutting down Clipder FastAPI server...")


app = FastAPI(
    title="Clipder API",
    description="Twitch clip curation and upload API",
    version="1.0.0",
    lifespan=lifespan,
)

# CRITICAL: Add CORS middleware FIRST, before any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Don't require credentials for CORS
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all response headers
    max_age=3600,  # Cache preflight for 1 hour
)

# Add secondary middleware to guarantee CORS headers on ALL responses
app.add_middleware(CORSGuaranteeMiddleware)


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
async def websocket_leaderboard(websocket: WebSocket):
    ws_manager = ConnectionManager.get_instance()
    try:
        logger.info(f"WebSocket connect attempt from {websocket.client}")
        await ws_manager.connect(websocket)
        logger.info(f"✅ WebSocket connected successfully")
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
        except:
            pass


@app.get("/")
async def root():
    return {"status": "ok", "app": "Clipder API", "version": "1.0.0"}


# Note: Detailed health checks at /api/v1/health, /api/v1/health/db, etc.


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
