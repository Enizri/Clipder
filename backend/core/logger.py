"""
Basic logging configuration for ClipApp backend.
Logs all API errors, database errors, and WebSocket events.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Get logger for this module
logger = logging.getLogger(__name__)


class ContextLogger:
    """Wrapper for logging with context information"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def info(self, message: str, context: Dict[str, Any] = None):
        """Log info with optional context"""
        if context:
            message = f"{message} | {context}"
        self.logger.info(message)

    def error(
        self, message: str, context: Dict[str, Any] = None, exc_info: bool = False
    ):
        """Log error with optional context"""
        if context:
            message = f"{message} | {context}"
        self.logger.error(message, exc_info=exc_info)

    def warning(self, message: str, context: Dict[str, Any] = None):
        """Log warning with optional context"""
        if context:
            message = f"{message} | {context}"
        self.logger.warning(message)

    def debug(self, message: str, context: Dict[str, Any] = None):
        """Log debug with optional context"""
        if context:
            message = f"{message} | {context}"
        self.logger.debug(message)


def get_logger(name: str) -> ContextLogger:
    """Get a logger instance"""
    return ContextLogger(name)


# Module-level loggers for common use cases
api_logger = get_logger("clipapp.api")
db_logger = get_logger("clipapp.database")
ws_logger = get_logger("clipapp.websocket")
task_logger = get_logger("clipapp.tasks")
cache_logger = get_logger("clipapp.cache")


def log_api_error(endpoint: str, method: str, status_code: int, error: str):
    """Log API endpoint error"""
    api_logger.error(
        f"API Error: {method} {endpoint}",
        context={
            "status_code": status_code,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def log_database_error(query: str, error: str):
    """Log database error"""
    db_logger.error(
        "Database Error",
        context={
            "query": query[:100] + "..." if len(query) > 100 else query,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def log_websocket_event(event: str, client_count: int):
    """Log WebSocket event"""
    ws_logger.info(
        f"WebSocket {event}",
        context={
            "connected_clients": client_count,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def log_task_execution(task_name: str, duration: float, status: str):
    """Log background task execution"""
    task_logger.info(
        f"Task {task_name} completed",
        context={
            "status": status,
            "duration_ms": f"{duration * 1000:.2f}",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
