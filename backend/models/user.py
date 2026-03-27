from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.vote import Vote
    from backend.models.user_streamer import UserStreamer


class UserRole(str, enum.Enum):
    USER = "USER"
    PRO = "PRO"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.USER, nullable=False
    )
    twitch_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, unique=True
    )
    twitch_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    twitch_access_token: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    twitch_refresh_token: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Lazy-load relationships (only load when explicitly accessed)
    votes: Mapped[list["Vote"]] = relationship(
        "Vote", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    streamers: Mapped[list["UserStreamer"]] = relationship(
        "UserStreamer",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
