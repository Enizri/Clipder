import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # One vote per user per clip
    __table_args__ = (UniqueConstraint("user_id", "clip_id", name="unique_vote"),)

    user: Mapped["User"] = relationship("User", back_populates="votes")
    clip: Mapped["Clip"] = relationship("Clip", back_populates="votes")
