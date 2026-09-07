from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class UserStreamer(Base):
    __tablename__ = "user_streamers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    streamer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    streamer_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Which followed channels appear in the "For You" feed (user-configurable).
    include_in_for_you: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="streamers")
