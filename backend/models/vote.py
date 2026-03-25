from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.clip import Clip


class VoteType(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    clip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clips.id"), nullable=False, index=True
    )
    vote_type: Mapped[VoteType] = mapped_column(SQLEnum(VoteType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="votes")
    clip: Mapped["Clip"] = relationship("Clip", back_populates="votes")
